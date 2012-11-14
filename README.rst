Introduction
============

WebSphere Administration Console is an easy to use web interface to do WebSphere configuration. While as your infrastructure become larger and larger, simple configuration tasks like changing JVM heap size of a cluster become more and more time consuming and error prone if you do it manually using WebSphere Administration Console. Imagine you have a Cluster which has 60 JVM's. Automation start matters.

There are some other public available script which address the issue in some extend, but in my opinion they are either not general purpose or not flexible enough.

The goal of wastools/wasconf is to create an general purpose, flexible and easy to use WebSphere configuration automation tool to save WebSphere administrators from tedious WebSphere configuration tasks, so they can focus on more meaningful things or simply make their life easier.

I believe you can get the idea after going through the following working example::

    ---
    # Modify JVM settings of all application servers in cluster SampleCluster
    #
    ACTION: Modify
    OBJECTS: JavaVirtualMachine{Server[clusterName='SampleCluster']}
    ATTRIBUTES:
        genericJvmArguments: -Xdisableexplicitgc -Xgcpolicy:gencon -Xgcthreads4 -Xjit:disableInterpreterProfiling -Xlp -Xmn768m -Xmos768m -Xnoloa -Xscmx256m
        initialHeapSize: 1536
        maximumHeapSize: 1536
        verboseModeGarbageCollection: True
    ---
    # Modify session settings of all application servers in cluster SampleCluster
    #
    ACTION: Modify
    OBJECTS: TuningParams{SessionManager{Server[clusterName='SampleCluster']}}
    ATTRIBUTES:
        maxInMemorySessionCount: 10000
        writeContents: ONLY_UPDATED_ATTRIBUTES
        writeFrequency: TIME_BASED_WRITE
        writeInterval: 300
        scheduleInvalidation: true
        invalidationSchedule:
        firstHour: 0
        secondHour: 2
    ---
    # Modify WebContainer thread pool settings of all application servers in cluster SampleCluster
    #
    ACTION: Modify
    OBJECTS: ThreadPool{Server[clusterName='SampleCluster']}[name='WebContainer']
    ATTRIBUTES:
        minimumSize: 20
        maximumSize: 20
    ---
    # Modify setting of a data source named WebSphere DB2 DataSource in cluster SampleCluster
    #
    ACTION: Modify
    OBJECTS: DataSource{ServerCluster[name='SampleCluster']}[name='WebSphere DB2 DataSource']
    ATTRIBUTES:
        statementCacheSize: 1000
    ---
    # Modify connection pool settings of the above datasource
    #
    ACTION: Modify
    OBJECTS: ConnectionPool{DataSource{ServerCluster[name='SampleCluster']}[name='WebSphere DB2 DataSource']}
    ATTRIBUTES:
        connectionTimeout: 3
        maxConnections: 30
        minConnections: 10
        reapTime: 300
        unusedTimeout: 1200
        agedTimeout: 1800
        purgePolicy: EntirePool
    ---
    # Delete all JVM properties of all application servers in cluster SampleCluster
    #
    ACTION: Modify
    OBJECTS: "JavaVirtualMachine{Server[clusterName='SampleCluster']}"
    "
    ATTRIBUTES:
        systemProperties: []
    ---
    # Create the following JVM properties for all application servers in cluster SampleCluster
    #
    ACTION: Modify
    OBJECTS: "JavaVirtualMachine{Server[clusterName='SampleCluster']}"
    "
    ATTRIBUTES:
        systemProperties: 
        - name: com.ibm.ws.cache.CacheConfig.filterInactivityInvalidation
          value: "true"
        - name: com.ibm.ws.cache.CacheConfig.useServerClassLoader
          value: "true"
        - name: com.ibm.websphere.xs.dynacache.disable_recursive_invalidate
          value: "true"
        - name: com.ibm.websphere.xs.dynacache.ignore_value_in_change_event
          value: "true"
        - name: com.ibm.websphere.xs.dynacache.enable_compression
          value: "true"
        - name: com.ibm.websphere.xs.dynacache.topology
          value: remote
        - name: com.ibm.ws.cache.CacheConfig.cacheProviderName
          value: com.ibm.ws.objectgrid.dynacache.CacheProviderImpl
    ---
    # Create a single JVM property for all application servers in cluster SampleCluster
    #
    ACTION: Create
    TYPE: Property
    PARENTS: "JavaVirtualMachine{Server[clusterName='SampleCluster']}"
    "
    ATTRIBUTES:
        name: com.ibm.ws.cache.CacheConfig.cacheProviderName
        value: com.ibm.ws.objectgrid.dynacache.CacheProviderImpl
    ---
    # Delete JVM properties with the following names on all application servers in cluster SampleCluster
    #
    ACTION: Delete
    OBJECTS: "Property{JavaVirtualMachine{Server[clusterName='SampleCluster']}"}[
              name='com.ibm.ws.cache.CacheConfig.filterInactivityInvalidation' |
              name='com.ibm.ws.cache.CacheConfig.useServerClassLoader' |
              name='com.ibm.websphere.xs.dynacache.disable_recursive_invalidate' |
              name='com.ibm.websphere.xs.dynacache.ignore_value_in_change_event' |
              name='com.ibm.websphere.xs.dynacache.enable_compression' |
              name='com.ibm.websphere.xs.dynacache.topology' |
              name='com.ibm.ws.cache.CacheConfig.cacheProviderName'
          ]"
    ...
 

Installation
============

Requirements
------------

- WebSphere (6.1 and 7.0 tested)
- Jython >= 2.5

Instructions
------------

The recommended place to deploy this tool is a Linux machine which is capable of connecting to your WebSphere environments at the network level. Your Linux laptop or workstation is a good one. By following the instructions below, you will have a wastools/wasconf installation which is capable of performing configuration tasks against any WebSphere V6.1 or V7.0 environments.

- Download and Install IBM JDK V6: http://www.ibm.com/developerworks/java/jdk
- Download and Install Jython 2.5.3: http://search.maven.org/remotecontent?filepath=org/python/jython-installer/2.5.3/jython-installer-2.5.3.jar http://wiki.python.org/jython/InstallationInstructions
- Build a WebSphere administration thin client: http://pic.dhe.ibm.com/infocenter/wasinfo/v7r0/topic/com.ibm.websphere.nd.multiplatform.doc/info/ae/ae/txml_adminclient.html
- Modify the wsadmin.sh (created in step 3) by adding jython.jar (installed on step 2) to the beginning of CLASSPATH, for example ::

    C_PATH="/opt/jython/jython.jar:${WAS_HOME}/properties:${WAS_HOME}/com.ibm.ws.admin.client_7.0.0.jar:${WAS_HOME}/com.ibm.ws.security.crypto.jar"

- Download and Unzip the code of wastools/wasconf: https://github.com/wfrank/wastools/archive/master.zip
- Modify the paths in bin/wasconf, lib/wasconf.py to the actual ones.
