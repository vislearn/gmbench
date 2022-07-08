# Graph Matching Benchmark

This repository contains the code necessary to run the graph matching benchmark
for ECCV 2022 paper “A Comparative Study of Graph Matching Algorithms in
Computer Vision”.


## Design

For all methods we build Linux containers so that the environment as well as
the solvers are reproducible. The usage of containers makes it easy to run the
benchmark on the local computer as well as in compute clusters.

The source code of each method is fetched from the Internet. For the case that
source code is no longer online, we preserve a historical copy of the
repositories. The container build scripts will pin each method to a specific
version or commit id to preserve reproducibility.

To make local usage straight-forward we use Podman to create and run the
containers. The containers also work with Docker, but using Podman has some
nice usability advantages (no daemon necessary, possible to run it as
unpriveleged user without setup).

For usage in HPC clusters we provide a small script to transform the Podman
containers into singluarity containers (i.e. squashfs images). Additionally, we
provide SLURM scheduling scripts so that everything can be scheduled in one
run.

After running the benchmark the log files will be parsed and all datapoints
will be written into an Sqlite database. We provide helper tools to work with
the database. For example, we can export the data as JSON objects, check that
all solvers were executed successfully, generate tables and plots, etc.

On important aspect is that running on HPC will sometimes create some hard to
debug problems. We provide script to detect "anomalies" like non-deterministic
runs or runs that were much slower than other runs. By purging those anomalies
we can re-execute the affected trials on the HPC cluster to get consistent
results.


## Directory Structure

```
.              -> main helper scripts for building containers
├── bin        -> scripts meant to be executed
├── container  -> source definition for all containers
├── python     -> Python module code
└── slurm      -> batch scripts for usage with SLURM scheduler
```


## Building and Running the Linux Containers

Make sure to have Podman (or Docker) installed. For the Matlab methods you will
also need a Matlab license server in your network. If you do not have a Matlab
license server available, you should comment out the line for the Matlab
container in `build-containers`.

```sh
export MATLAB_LICENSE_SERVER=port@hostname
./build-containers
```

If you enter `podman images` you should now see a list of `gmbench/*` container
images.

To run the e.g. `dd-ls0` method, you can spawn a new container and run the
method:

```sh
podman run --rm -ti gm-benchmark/dd-ls
# Inside container:
dd-ls0 car 1 1
```

The above will obviously fail if no datasets are present. To make a folder with
all datasets available inside the container you can use something like `podman
run --volume ./datasets/:/home/matlab/datasets --rm -ti gm-benchmark/dd-ls`.
This will make the `dataset` directory of the current directory available
inside the container.

To run Matlab methods you should add the `--env MATLAB_LICENSE_SERVER` to pass
through the `$MATLAB_LICENSE_SERVER` environment variable.


## Command Line Arguments

For each method `dd-ls0`, `dd-ls3`, `fm`, etc. there is wrapper script
availabe in the approriate container. Calling convention is always the same and
the scripts all take the same arguments:

1. dataset name (e.g. `car`)
2. index of instance (from 1 to number of dataset instances)
3. number of trial

Each method will store the results in the directory
`benchmark/$trial/$method/$dataset/$dataset$instance`.


## Log File Processing

Use the script `bin/process-log` to process the log files. There is a SLURM
batch script available to process all log files (`slurm/process-logs.batch`).

The script will parse the log file with the correct parser and store the
results in a JSON encoded file. The format of the file looks like this:

```json
{
    "method": "dd-ls0",
    "trial": 1,
    "dataset": "car",
    "instance": 1,
    "datapoints": [
        {
            "time": 0.000143729,
            "value": -1873.5035770000002,
            "bound": -2667.3177000000005,
            "assignment": [1, 2, 3, ...]
        },
        { ... }
    ]
}
```


## Running on HPC Cluster with SLURM scheduler

Running the benchmark on a HPC cluster has the advantage of being conveniently
fast (depending on the size of the cluster). However, it also imposes
additional problems: We loose control of the hardware and other cluster users
can impact the performance of our compute node.

To counter these problems we did the following:

1. Specify a SLURM partition consisting only of nodes with identical hardware
   specs.
2. Copy input data from network filesystem to local filesystem before
   benchmarking. This is done inside the SLURM batch script.
3. Specify `--exclusive` so that no other users are allowed on our nodes.
4. Run fewer tasks than CPU threads available (so that different tasks do not
   compete for the memory bus).

We run the benchmark on nodes having two AMD EPYC 7702 2.0 GHz processor. One
processor has 64 cores (2 SMT threads each). In total we have 128 cores (256
SMT threads). To schedule at max 32 tasks on such a node, we used the following
SLURM parameters:

```
--partition $partition_name
--exclusive
--ntasks=32
--cpus-per-task=8
--mem-per-cpu=1000M
```

If you want to run the benchmark on a different cluster, you will most like
have to recompute these values (e.g. 256 cores / 32 tasks = 8 cpus-per-task)
and change the preamble of the SLURM batch scripts in `slurm/*.batch`!

To export the singularity images, first build the Podman containers locally
(`./build-containers`) and afterwards run `./build-images'. Use `./deploy-hpc
username@hpchost:/path/to/workspace` to copy all necessary files to cluster
(beware that it will use ˋrsync --deleteˋ).

On the HPC cluster change into the workspace directory and then run, for
example, `sbatch slurm/dd-ls.batch $trial`. For each family of solvers there is
a dedicated SLURM batch script. Note that you have to export the environment
variable `$MATLAB_LICENSE_SERVER` before calling sbatch if you want to run the
Matlab methods.


## Container Directory Structure

`/usr/local/bin`: Contains wrapper script for each method. E.g. in the `dd-ls`
container there will be a wrapper script `dd-ls0` that runs the benchmark for
this specific method. It sets all necessary parameters and knows where the
“real” executable is located. Most of the time there will be multiple wrapper
scripts that call the same method with different parameters.

`/usr/local/lib/gmbench`: Contains helper functions that are sourced from above
mentioned wrapper scripts.
