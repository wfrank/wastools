Introduction
============

WebSphere Administration Console is an easy to use web interface to do WebSphere configuration. While as your infrastrature become larger and larger, simple configuration tasks like changing JVM heap size of a cluster become more and more time consuming and error prone if you do it manually using WebSphere Administration Console. Imagine you have a Cluster which has 60 JVM's. Automation start matters.

There are some other public avaiable script which address the issue in some extend, but in my opinion they are either not general purpose or not flexiable enough.

The goal of wastools/wasconf is to create an general purpose, flexiable and easy to use WebSphere configuration automation tool to save WebSphere administrators from tedious WebSphere configuration tasks, so they can focus on more meanningful things or simply make their life easier.

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
 
