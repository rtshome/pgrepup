pgrepup - PostgreSQL REPlicate and UPgrade
=====

pgrepup is a tool written in Python for upgrading a PostgreSQL cluster to a new major version using logical replication
and pglogical extension.

pgrepup simplifies the setup of 2nd Quadrant's pglogical extension giving hints for configuring correctly source and
destination pgsql clusters.

The supported versions of PostgreSQL are 9.4, 9.5 and 9.6.

## Quick start

### Requirements

`pgrepup` requires both a source and a destination PostgreSQL cluster.

The clusters can have been installed into the same server or on different hosts.

`pgrepup` doesn't need to be installed into the clusters' server.
It can be safely executed from a remote host that can access both pgsql clusters. In this case, it's recommended that
SSL is enabled in `pg_hba.conf` of both clusters because pgsql credentials are sent over the network.

### Installation

`pip install pgrepup`

All versions of Python >= 2.7 are supported.

### Replication

A pgsql cluster can be replicated and upgraded through these four steps:

1. `pgrepup config`: a simple wizard asks the basic configuration parameters needed by pgrepup
    - Source and Destination database cluster
    - Directory where to store temporary files
2. `pgrepup check`: various checks are done both in Source and Destination cluster
    - if a check fails, pgrepup outputs a hint for helping you to configure each cluster
3. `pgrepup setup`: if the checks are all ok, this setup installs and configure pglogical in both pgsql clusters
4. `pgrepup start`: start the replication process

After the start command, you can monitor the replication process using the command `pgrepup status`.

The output of the status command displays an entry for each database of the source cluster along with the status
reported by pglogical extension.
The status can be one of the following three values:

- initializing: pglogical is copying data from source to destination cluster
- replicating: pglogical is using pgsql logical replication to replicate and upgrade new data changed into the source
  cluster
- down: replication is down, check the PostgreSQL log in both clusters

After a while where the databases are all in `initializing` status, each database status will change to `replicating` as
the data is progressively copied from the source cluster.

### Upgrade

When the replication is working fine, you can switch your application to the Destination cluster at any moment.
Just follow these simple steps:
- stop your application connecting to the source cluster
- ensure no more connections are made to the source cluster
- stop replication using `pgrepup stop` command
- change the DSN in your application (or in your connection pooler) and point to the destination cluster
- start your application
- upgrade done! :-)

### Uninstall

pglogical and others settings applied by `pgrepup` can be removed at any time using the command:

`pgrepup uninstall`

## Caveats

`pgrepup` is still experimental. Please feel free to open an issue on github if you encounter problems.

### DDL commands

DDL commands issued in a source cluster database are not replicated to the destination cluster. This is a limit of how
pgsql logical replication works.
Use the `pglogical.replicate_ddl_command SQL function on the source database in order to replicate the DDL on the
destination cluster.

Be aware that, at the moment, pgrepup doesn't handle the automatic subscription of newly created tables added using
pglogical.replicate_ddl_command .
The recommended procedure is to re-start the replication process using the stop, setup and start commands.
``
A solution is in the works and will be available in the next release of pgrepup.

### Sequences

Sequences are replicated between source and destination cluster. When the stop command is given, pgrepup uses pglogical
function to do a final synchronization of each sequence value.
The pglogical function adds an artificial +1000 value to the actual sequence value:
[see this discussion](https://groups.google.com/a/2ndquadrant.com/forum/#!topic/bdr-list/6GA3AELQk8M) on pglogical
mailing list on google groups

### High number of databases

pgrepup has been tested with success to replicate several clusters different both in size and database number. 

However, after issuing a start command, pglogical background workers start all simultaneously to dump the data of the
source database into the destination database.

This can generate very high cpu/disk load on both clusters depending on the number of databases to replicate.

A feature that enables to limit the number of databases that are dumped concurrently is in the works.

## License and contributions

pgrepup is licensed using GPL-3 license. Contributions are welcome!