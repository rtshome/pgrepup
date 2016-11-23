pgrepup - PostGreSQL REPlicate and UPgrade
=====

pgrepup is a tool for upgrading a PostGreSQL cluster to a new major version using logical replication and pglogical
extension.

pgrepup is actually a wrapper built around 2nd Quadrant pglogical extension and it simplifies its setup giving
hints for configuring correctly source and destination pgsql clusters.

The PostGreSQL versions supported are currently 9.4, 9.5 and 9.6

## Quick start

### Requirements

`pgrepup` requires both a source and a destination PostGreSQL cluster.

The clusters can have been installed into the same server or on different hosts.

`pgrepup` doesn't need to be installed into the clusters' server.
It can be safely executed from a remote host that can access both pgsql clusters. In this case, it's recommended that
SSL is enabled in `pg_hba.conf` of both clusters because pgsql credentials are sent over the network.

### Installation

`pip install pgrepup`

All versions of Python from 2.7 to 3.5 are supported.

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
- down: replication is down, check the PostGreSQL log in both clusters

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

It has been tested with success to replicate several clusters different both in size and database number. However the
dump of all the databases that happens after the `pgrepup start` command could generate very high cpu/disk load because
it's launched in parallel in all the databases.

A feature that enables to limit the number of databases that are dumped concurrently is in the works.


