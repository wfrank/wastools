from __future__ import with_statement

import os
import re
import sys
import pdb
import profile

from pprint import pprint
from weakref import WeakValueDictionary

home = '/home/wfrank/tools/wastools'
#home = os.sep.join(os.path.abspath(__file__).split(os.sep)[0:-2])
sys.path.append(home + '/lib')

import yaml
from ply import lex
from ply import yacc
from argparse import ArgumentParser


class MetaData(object):

    def __init__(self, name):
        output = AdminConfig.parents(name)
        if output.startswith('WASX7351I'):
            self.parents = None
        else:
            self.parents = output.splitlines()

        self.attributes = dict([
            l.split(' ', 1) for l in AdminConfig.attributes(name).splitlines()
        ])

        pattern = r'(?P<key>[^ ]+) +(?P<type>[^ ]+)( +(?P<value>[^ ]+))?'
        self.defaults = dict([
            re.match(pattern, l).group(1, 4)
            for l in AdminConfig.defaults(name).splitlines()[1:]
        ])

        pattern = r'(?P<key>[^ ]+) +(?P<type>[^ ]+)'
        output = AdminConfig.required(name)
        if output.startswith('WASX7361I'):
            self.required = None
        else:
            self.required = dict([
                re.match(pattern, l).group(1, 2)
                for l in output.splitlines()[1:]
            ])

        output = AdminConfig.listTemplates(name)
        self.templates = output.splitlines()


class BaseType(object):

    __cache__ = WeakValueDictionary()

    def __new__(cls, id):

        if id in cls.__cache__:
            return cls.__cache__[id]
        else:
            return object.__new__(cls, id)

    def __init__(self, id):

        if id in self.__cache__:
            return

        self.id = id

        pattern = r'^\[(?P<key>[^ ]+) (?P<value>.+)\]$'
        attributes = [
            re.match(pattern, l).groups()
            for l in AdminConfig.show(id).splitlines()
        ]

        for k, v in attributes:
            v = self.__meta__.attributes[k] == 'int' and int(v) or v
            v = self.__meta__.attributes[k] == 'boolean' and bool(v) or v
            v = self.__meta__.attributes[k] == 'String' and v.strip('"') or v
            setattr(self, k, v)

        self.__cache__[id] = self

    def __getattr__(self, name):
        if name in self.__meta__.defaults:
            return self.__meta__.defaults[name]
        if name in self.__meta__.attributes:
            return None
        raise AttributeError

    def __str__(self):
        return self.id

    def __repr__(self):
        return str(self)


class ConfigType(object):

    models = AdminConfig.types().splitlines()

    __cache__ = WeakValueDictionary()

    def __new__(cls, name):

        if name in cls.__cache__:
            return cls.__cache__[name]

        if name not in cls.models:
            raise SyntaxError('%s is not a valid configuration type' % name)

        metadata = MetaData(name)

        t = type(name, (BaseType,), {'__meta__': metadata})
        cls.__cache__[name] = t

        return t


class Expression(object):

    operations = {
        '=': lambda self, o: getattr(o, self.identifier) == self.value,
        '>': lambda self, o: getattr(o, self.identifier) >= self.value,
        '<': lambda self, o: getattr(o, self.identifier) <= self.value,
        '~': lambda self, o: bool(re.match(self.value, getattr(o, self.identifier)))
    }

    def __init__(self, identifier, operator, value):
        self.identifier = identifier
        self.operator = operator
        self.value = value

    def evaluate(self, object):
        result = self.operations[self.operator](self, object)
        return result

    def __str__(self):
        return '%s%s%s' % (self.identifier, self.operator, self.value)

    def __repr__(self):
        return str(self)


class BinaryExpression(object):

    operations = {
        '|': lambda self, o: self.left.evaluate(o) | self.right.evaluate(o),
        '&': lambda self, o: self.left.evaluate(o) & self.right.evaluate(o),
    }

    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def evaluate(self, object):
        return self.operations[self.operator](self, object)

    def __str__(self):
        return '%s%s%s' % (repr(self.left), self.operator, repr(self.right))

    def __repr__(self):
        return str(self)


class NegativeExpression(object):

    def __init__(self, expression):
        self.expression = expression

    def evaluate(self, object):
        return not self.expression.evaluate(object)

    def __str__(self):
        return '!%s' % self.expression

    def __repr__(self):
        return str(self)


class Selector(object):

    def __init__(self, model, ancestor=None, expression=None, descendant=None):
        self.model = ConfigType(model)
        self.ancestor = ancestor
        self.expression = expression
        self.descendant = descendant

    def select(self):
        if self.ancestor:
            objects = reduce(lambda x, y: x | set(y), [
                [self.model(i) for i in AdminConfig.list(self.model.__name__, a.id).splitlines()]
                for a in self.ancestor.select()
            ], set())

        else:
            objects = set([self.model(i) for i in AdminConfig.list(self.model.__name__).splitlines()])
        if self.expression:
            objects = set([o for o in objects if self.expression.evaluate(o)])
        if self.descendant:
            objects = self.descendant.filter(self.model, objects)
        return objects

    def filter(self, objects):
        return set([o
            for o in objects
                if set([AdminConfig.list(self.model, o).splitlines()])
                 & self.select()
        ])

    def __str__(self):
        result = self.model.__name__
        if self.ancestor:
            result += '{' + str(self.ancestor) + '}'
        if self.expression:
            result += '[' + str(self.expression) + ']'
        if self.descendant:
            result += '(' + str(self.descendant) + ')'
        return result

    def __repr__(self):
        return str(self)


class BinarySelector(object):

    select_operations = {
        '|': lambda self: self.left.select() | self.right.select(),
        '&': lambda self: self.left.select() & self.right.select(),
        '-': lambda self: self.left.select() - self.right.select(),
        '^': lambda self: self.left.select() ^ self.right.select(),
    }

    filter_operations = {
        '|': lambda self, o: self.left.filter(o) | self.right.filter(o),
        '&': lambda self, o: self.left.filter(o) & self.right.filter(o),
        '-': lambda self, o: self.left.filter(o) - self.right.filter(o),
        '^': lambda self, o: self.left.filter(o) ^ self.right.filter(o),
    }

    def __init__(self, left, operator, right):
        self.left = left
        self.right = right
        self.operator = operator
        if not left.model == right.model:
            raise ValueError("Child selectors of binary selector must have the same configuration object type")
        self.model = left.model

    def select(self):
        return self.select_operations[self.operator](self)

    def filter(self, objects):
        return self.filter_operations[self.operator](self, objects)

    def __str__(self):
        return '%s%s%s' % (self.left, self.operator, self.right)

    def __repr__(self):
        return str(self)


class NegativeSelector(object):

    def __init__(self, selector):
        self.selector = selector
        self.model = selector.model

    def select(self):
        model = self.selector.model
        objects = set([model(i) for i in AdminConfig.list(model).splitlines()])
        return objects - self.selector.select()

    def filter(self, objects):
        return objects - self.selector.filter(objects)

    def __str__(self):
        return '!%s' % self.selector

    def __repr__(self):
        return str(self)


class SelectorLexer(object):

    tokens = ('identifier', 'boolean', 'integer', 'string')

    literals = ('{', '[', '(', ')', ']', '}', ',', '&', '|', '!', '=', '~', '>', '<')

    t_ignore = ' \t'
    t_identifier = '[A-Za-z_][\w_]*'

    def t_boolean(self, t):
        r'true|false'
        t.value = bool(self, t.value)
        return t

    def t_integer(self, t):
        r'\d+'
        t.value = int(t.value)
        return t

    def t_string(self, t):
        r'\'[^\']+\''
        t.value = t.value.strip("'")
        return t

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def __init__(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)

    def input(self, data):
        return self.lexer.input(data)

    def token(self):
        return self.lexer.token()


class SelectorParser(object):

    tokens = SelectorLexer.tokens

    literals = SelectorLexer.literals

    precedence = (
        ('left' , '&'),
        ('left' , '|'),
        ('right', '!'),
    )

    def p_selector_ancestors_attributes_descendants(self, p):
        "selector : identifier '{' selectors '}' '[' expression ']' '(' selectors ')'"
        p[0] = Selector(p[1], p[3], p[6], p[9])

    def p_selector_ancestors_attributes(self, p):
        "selector : identifier '{' selectors '}' '[' expression ']'"
        p[0] = Selector(p[1], p[3], p[6])

    def p_selector_attributes_descendants(self, p):
        "selector : identifier '[' expression ']' '(' selectors ')'"
        p[0] = Selector(p[1], expression=p[3], descendants=p[6])

    def p_selector_ancestors_descendants(self, p):
        "selector : identifier '{' selectors '}' '(' selectors ')'"
        p[0] = Selector(p[1], ancestors=p[3], descendants=p[6])

    def p_selector_ancestors(self, p):
        "selector : identifier '{' selectors '}'"
        p[0] = Selector(p[1], p[3])

    def p_selector_attributes(self, p):
        "selector : identifier '[' expression ']'"
        p[0] = Selector(p[1], expression=p[3])

    def p_selector_descendants(self, p):
        "selector : identifier '(' selectors ')'"
        p[0] = Selector(p[1], descendants=p[3])

    def p_selector(self, p):
        "selector : identifier"
        p[0] = Selector(p[1])

    def p_selectors_binary(self, p):
        '''selectors : selector '|' selectors
                     | selector '&' selectors
                     | selector '+' selectors
                     | selector '-' selectors
                     | selector '^' selectors'''
        p[0] = BinarySelector(p[1], p[2], p[3])

    def p_selectors_negative(self, p):
        "selectors : '!' selectors"
        p[0] = NegativeSelector(p[1])

    def p_selectors_parenthesized(self, p):
        "selectors : '(' selectors ')'"
        p[0] = p[2]

    def p_selectors_single(self, p):
        "selectors : selector"
        p[0] = p[1]

    def p_expression_binary(self, p):
        '''expression : expression '|' expression
                      | expression '&' expression'''
        p[0] = BinaryExpression(p[1], p[2], p[3])

    def p_expression_negative(self, p):
        "expression : '!' expression"
        p[0] = NegativeExpression(p[2])

    def p_expression_parenthesized(self, p):
        "expression : '(' expression ')'"
        p[0] = p[2]

    def p_expression(self, p):
        '''expression : identifier '=' value
                      | identifier '~' value
                      | identifier '>' value
                      | identifier '<' value'''
        p[0] = Expression(p[1], p[2], p[3])

    def p_value(self, p):
        '''value : boolean
                 | integer
                 | string'''
        p[0] = p[1]

    def p_error(self, p):
        if p:
            print("Syntax error at '%s'" % p.value)
        else:
            print("Syntax error at EOF")

    def __init__(self, **kwargs):
        self.lexer = SelectorLexer()
        self.parser = yacc.yacc(module=self, **kwargs)

    def parse(self, data, **kwargs):
        return self.parser.parse(data, lexer=self.lexer, **kwargs)


class InfoCommand(object):

    def __init__(self, options):
        self.options = options

    def __call__(self):
        t = ConfigType(self.options.model)
        print 'Infomation about Configuration Type: %s' % self.options.model
        for c in self.options.contents:
            print c
            pprint(getattr(t.__meta__, c))


class QueryCommand(object):

    def __init__(self, options):
        self.options = options

    def __call__(self):
        parser = SelectorParser()
        selector = parser.parse(self.options.selector)
        objects = selector.select()
        print 'Query Result for Selector: %s (%d objects selected)' % (self.options.selector, len(objects))
        for o in objects:
            print o
            if self.options.verbose:
                pprint(o.__dict__)


def listlize(input):
    if type(input) == bool:
        return str(input).lower()
    elif type(input) == list:
        return [listlize(i) for i in input]
    elif type(input) == dict:
        return [[k, listlize(v)] for k, v in input.items()]
    else:
        return input


class ActionFactory(object):

    __registry__ = {}

    @classmethod
    def register(cls, action_class):
        class_name = action_class.__name__
        key = class_name.endswith('Action') and class_name.replace('Action', '').lower()
        if key == False:
            raise ValueError('%s is not a valid Action class name' % class_name)
        if key != '':
            cls.__registry__[key] = action_class

    def __new__(cls, name):
        key = name.lower()
        if key in cls.__registry__:
            return cls.__registry__[key]
        else:
            raise ValueError('%s is not a valid Action type' % name)


class ActionMeta(type):

    def __init__(cls, name, bases, attrs):
        ActionFactory.register(cls)


class Action(object):

    __metaclass__ = ActionMeta

    __counter__ = 0

    def __init__(self, options, params):
        Action.__counter__ += 1
        self.index = Action.__counter__
        self.options = options
        self.params = params
        self.parser = SelectorParser()

    def __call__(self):
        print 'Start executing action #%d' % self.index
        try:
            self.prepare()
            self.execute()
        except Exception:
            print 'Failed exectuing action #%d, please review the exceptions' % self.index
            raise
        else:
            self.confirm()

    def confirm(self):
        output = AdminConfig.queryChanges()

        if output.startswith('WASX7241I'):
            changes = []
        else:
            changes = [c.strip() for c in output.splitlines()[1:]]

        print 'Number of configuration files changed: %d' % len(changes)
        if self.options.verbose:
            for c in changes:
                print '    ', c

        if len(changes) > 0:
            if self.options.mode == 'save':
                AdminConfig.save()
                print 'All changes have been saved'
            elif self.options.mode == 'reset':
                AdminConfig.reset()
                print 'All changes have been reset'
            else:
                raise ValueError('Invalid operation mode, valid choices are save or reset')


class CreateAction(Action):

    def __init__(self, options, params):
        super(CreateAction, self).__init__(options, params)
        self.model = ConfigType(self.params['TYPE'])
        self.selector = self.parser.parse(self.params['PARENTS'],
                                                  debug=self.options.debug)
        parent_model = self.selector.model
        child_model = self.model

        if child_model.__meta__.parents and parent_model.__name__ not in child_model.__meta__.parents:
            print child_model.__meta__.parents
            raise ValueError('%s is not a valid parent for configuration type: %s\nValid choices are: %s'
                             % (parent_model.__name__, child_model.__name__,
                                ', '.join(child_model.__meta__.parents)))
        self.attributes = self.params['ATTRIBUTES']
        for a in self.attributes:
            if a not in child_model.__meta__.attributes:
                raise ValueError('%s is not a valid attribute of configuration type: %s\nValid choices are: %s'
                                 % (a, child_model.__name__, ', '.join(child_model.__meta__.attributes)))
        if child_model.__meta__.required:
            missings = [a for a in child_model.__meta__.required if a not in self.attributes]
            if len(missings) > 0:
                raise ValueError('Missing required attribute for configuration type %s: %s'
                                 % (child_model.__name__, ', '.join(missings)))
        self.template = self.params.get('TEMPLATE')
        if self.template and self.template not in child_model.__meta__.templates:
            raise ValueError('%s is not a valid template for configuration type: %s\nValid choices are:\n%s'
                             % (self.template, child_model.__name__,
                             '\n    '.join(child_model.__meta__.templates)))
        self.parrent_attribute_name = self.params.get('PARRENT_ATTRIBUTE_NAME')
        if self.parrent_attribute_name \
                and self.parrent_attribute_name not in parent_model.__meta__.attributes:
            raise ValueError('%s is not a valid attribute of parent configuration type: %s'
                             % (a, parent_model.__name__))

    def prepare(self):
        self.parents = self.selector.select()
        print 'Number of parent configuration objects selected: %d' % len(self.parents)
        if self.options.verbose:
            for p in self.parents:
                print '    ', p
        self.attributes = listlize(self.attributes)

    def execute(self):
        for p in self.parents:
            if self.template:
                output = AdminConfig.createUsingTemplate(self.model.__name__, p,
                                                         self.attributes,
                                                         self.template)
            elif self.parrent_attribute_name:
                output = AdminConfig.create(self.model.__name__, str(p), self.attributes,
                                            self.parrent_attribute_name)
            else:
                output = AdminConfig.create(self.model.__name__, str(p), self.attributes)

#            if output != '':
#                raise SystemError(output)


class ModifyAction(Action):

    def __init__(self, options, params):
        super(ModifyAction, self).__init__(options, params)
        self.selector = self.parser.parse(self.params['OBJECTS'],
                                                  debug=self.options.debug)
        self.attributes = self.params['ATTRIBUTES']
        for a in self.attributes:
            if a not in self.selector.model.__meta__.attributes:
                raise ValueError('%s is not a valid attribute of configuration type: %s'
                                 % (a, self.selector.model.__name__))

    def prepare(self):
        self.objects = self.selector.select()
        print 'Number of configuration objects to be modified: %d' % len(self.objects)
        if self.options.verbose:
            for o in self.objects:
                print '    ', o

        self.attributes = listlize(self.attributes)

    def execute(self):
        for o in self.objects:
            output = AdminConfig.modify(str(o), self.attributes)
            if output != '':
                raise SystemError(output)


class DeleteAction(Action):

    def __init__(self, options, params):
        super(DeleteAction, self).__init__(options, params)
        self.selector = self.parser.parse(self.params['OBJECTS'],
                                                  debug=self.options.debug)

    def prepare(self):
        self.objects = self.selector.select()
        print 'Number of configuration objects to be deleted: %d' % len(self.objects)
        if self.options.verbose:
            for o in self.objects:
                print '    ', o

    def execute(self):
        for o in self.objects:
            output = AdminConfig.remove(str(o))
            if output != '':
                raise SystemError(output)


class ApplyCommand(object):

    def __init__(self, options):
        self.options = options
        self.actions = []
        try:
            module = os.path.join(home, 'conf', options.module + '.yaml')
            with open(module, 'r') as stream:
                counter = 0
                records = yaml.load_all(stream)
                for record in records:
                    counter += 1
                    action = record.get('ACTION')
                    if action == None:
                        raise ValueError('Missing ACTION directive in \
                                configuration module: %s, record #%d'
                                % (options.module, counter))
                    action = ActionFactory(action)(options, record)
                    action.index = counter
                    self.actions.append(action)
        except IOError:
            print 'Failed loading the configuration module: %s' % options.module
            raise

    def __call__(self):
        for action in self.actions:
            action()


class CheckCommand(object):

    def __init__(self, options):
        pass

    def __call__(self):
        pass


def main():

    parser = ArgumentParser(
        prog='wasconf',
        description='WebSphere configuration script.',
        epilog="for more information, please contact frank.wang@qvc.com."
    )

    subparsers = parser.add_subparsers(title='available configuration actions')

    info_parser = subparsers.add_parser('info', help='infomation about WebSphere configurtion types')
    query_parser = subparsers.add_parser('query', help='query infomation about WebSphere configurtion objects selected by Selector')
    apply_parser = subparsers.add_parser('apply', help='apply all actions in the configuration module')
    check_parser = subparsers.add_parser('check', help='check WebSphere configurtion objects')

    info_parser.add_argument('type', help='Name of the WebSphere configurtion type')
    info_parser.add_argument('contents', nargs='+', help='what kind of infomation you what to know about the configuration type')
    info_parser.set_defaults(command=InfoCommand)

    query_parser.add_argument('-v', '--verbose', action='store_true', required=False, help='would you like to show the attributes of the objects')
    query_parser.add_argument('selector', help='selector to query')
    query_parser.set_defaults(command=QueryCommand)

    apply_parser.add_argument('-d', '--debug', action='store_true', default=False, required=False, help='Enable debuging')
    apply_parser.add_argument('-v', '--verbose', action='store_true', default=False, required=False, help='Enable verbose output')
    apply_parser.add_argument('-m', '--mode', choices=('save', 'reset'), required=False, help='Mode of operation')
    apply_parser.add_argument('module', help='Name of the module which contains the settings you want to apply')
    apply_parser.set_defaults(command=ApplyCommand)

    check_parser.add_argument('-d', '--debug', action='store_true', default=False, required=False, help='Enable debuging')
    check_parser.add_argument('-v', '--verbose', action='store_true', default=False, required=False, help='Enable verbose output')
    check_parser.add_argument('-m', '--mode', choices=('save', 'reset'), required=False, help='Mode of operation')
    check_parser.add_argument('module', help='Name of the module which contains the settings you want to check')
    check_parser.set_defaults(command=CheckCommand)

    options = parser.parse_args(os.environ['OPTIONS'].split())
    command = options.command(options)

    command()

if __name__ == '__main__':

    main()
 #   profile.run('main()')

# vi: tabstop=4 shiftwidth=4 softtabstop=4 expandtab autoindent
