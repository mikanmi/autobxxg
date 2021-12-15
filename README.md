# autobxxg

autobxxg is a backup script written in Python3 language.

# Overview

autobxxg consist of one Python3 script and two systemd unit files.

The feature of autobxxg:

- Backup a logical volume of LVM.
- Prune the earlier backups automatically.
- Show information of the backups.
- Continuously backup on `systemd` timer.

You can restore a logical volume of LVM from the backups in a BorgBackup repository, of course you can restore a file from the backups.

## Python3 Script

"Backup" feature of autobxxg.py:

- Create a snapshot from a logical volume of LVM.
- Mount the snapshot everywhere.
- Backup the the snapshot mounted.

"Prune" feature of autobxxg.py:

- Prune the earlier backups except the later backups.

## systemd unit files

Provide systemd unit files for Interval Timer.

- autobxxg.timer is systemd timer unit.
- autobxxg.service is systemd service unit.

# Usage

## Configure

The configuration features in autobxxg.

### Configure autobxxg

`autobxxg.py` has many configuration variables in its source code.

Assign your environment to the following configurations.

### Explain autobxxg configururations

Explain configure with name, description and initial configuration:
|Name|Description|Initial Configuration|
|---|---|---|
|LOGICAL_VOLUMES|Tuple of logical volumes specified LV Path and filesystem type.|See below **Complex Initial Configuration**|
|BXXG_REPOSITORY|Path to BorgBackup repository|`"/var/borg/repo.borg"`|
|BXXG_PASS_PHRASE|Name of file containing passphrase accessing to repository|`".borg-passphrase"`|
|BXXG_PRUNE_KEEP_NUMBERS|The numbers of keeping latest archives related to times when autobxxg prunes|See below **Complex Initial Configuration**|
BXXG_EXCLUDE_PATTERNS|The patterns that autobxxg excludes files from backup archives|See below **Complex Initial Configuration**|

### Complex Initial Configuration

**LOGICAL_VOLUMES**

LOGICAL_VOLUMES is an array of which an element contains LV Path and filesystem type.
An element contains LV Path at the first element, filesystem type at the second element.

Pick up LV Path from the output of `lvdisplay` command and filesystem type from the output of `df -T` command

Initial Configuration is:

```python::autobxxg.py
(
    # LV Path,                 filesystem type
    ("/dev/ubuntu-vg/archive", "ext4"),
    ("/dev/ubuntu-vg/ubuntu-lv", "ext4"),
)
```

**BXXG_PRUNE_KEEP_NUMBERS**

BXXG_PRUNE_KEEP_NUMBERS is a dictionary of which an element contains `--keep-<interval>` of `borg prune` optional arguments.
An element contains `--keep-<interval>` string itself at Key, `--keep-<interval>` parameter at Value.

`borg prune --help` with more details.

Initial Configuration is:

```python::autobxxg.py
{
    "--keep-secondly": 0,
    "--keep-minutely": 0,
    "--keep-hourly": 24,
    "--keep-daily": 31,
    "--keep-weekly": 104,
    "--keep-monthly": 0,
    "--keep-yearly": 0,
}
```

**BXXG_EXCLUDE_PATTERNS**

BXXG_EXCLUDE_PATTERNS is an array which contains Exclude Pattern.
autobxxg excludes paths matching Exclude Pattern.
autobxxg will combine the mount point to lvm snapshot with Exclude Pattern if Exclude Pattern is absolute path.

`borg create --help` with more details.

Initial Configuration is:

```python::autobxxg.py
(
    "/tmp"
    "/var/cache",
    "/var/tmp",
    "/swap.img",
    "/root/.cache",
    "/home/*/.cache",
)
```

## Advanced Configure

```python::autobxxg.py
######################
# Advanced Configure #
######################
DEBUG_DRY_RUN: Final[bool] = False
LOGGER: Final[Logger] = logging.getLogger(__name__)
LOGGER_LOG_LEVEL: Final[int] = logging.INFO
LOGGER_LOG_FILENAME: Final[str] = "/var/log/autobxxg.log"

# The base directory where autobxxg mounts lvm snapshot.
MOUNT_BASE_DIRECTORY: Final[str]  = "/"

# The snapshot postfix with which autobxxg combine LV Name.
SNAPSHOT_POSTFIX: Final[str] = "-bxxg"

#
# Linux Commands
#

# Pass str.format with the following command and variables.
# str.format replace "{}" in the command to variables.

# Replace `{}` to mount path of snapshot LV.
MKDIR: Final[str]  = "mkdir -p {}"
# Replace `{}` to mount path of snapshot LV.
RMDIR: Final[str]  = "rmdir {}"

# Replace 1st `{}` to snapshot LV Name, 2nd `{}` LV Path of backup.
LVCREATE_SNAPSHOT: Final[str]  = "lvcreate -s -l 100%FREE -n {} {}"
# Replace `{}` to mount path of snapshot LV.
LVREMOVE: Final[str]  = "lvremove -f {}"

# Replace 1st `{}` to filesystem type, 2nd `{}` to snapshot LV Path, 3rd `{}` to mount path of snapshot LV.
MOUNT: Final[str]  = "mount -r -t {} {} {}"
# Replace `{}` to mount path of snapshot LV.
UMOUNT: Final[str]  = "umount -f {}"
```

## Deploy

Move the current directory to it contains this software.

```bash
~$ cd autobxxg
```

Create the passphrase file containing your passphrase to access BorgBackup repository.

```bash
~/autobxxg$ echo -n <your passphrase on BorgBackup> > .borg-passphrase
```

Copy the current directory(aka `autobxxg` directory) to `/usr/local/lib/`.

```bash
~/autobxxg$ sudo cp -R `pwd` /usr/local/lib/
```

Copy the systemd unit files to the systemd directory.

```bash
~/autobxxg$ sudo cp autobxxg.service autobxxg.timer /etc/systemd/system
```

Enable and start schedule timer.

```bash
~/autobxxg$ sudo systemctl enable --now autobxxg.timer
```

## Environment

autobxxg is running but not limited with the followings.

- Ubuntu: 20.10 Server
- LVM: 2.03.07(2) (2019-11-30)
- Python: 3.8.6
- BorgBackup: 1.1.15
- systemd: 246

## For your convenience

### Backup Repository

autobxxg depends on BorgBackup. Prepare BorgBackup repository.

```bash
sudo borg init -e repokey /var/borg/repo.borg
```

The command means initialize BorgBackup repository with passphrase.

See more details [Easy To Use on Official BorgBackup repository](https://github.com/borgbackup/borg/blob/master/README.rst#easy-to-use) if needed.

### Mount Backups

Mount Backup Repository of fuse.borgfs filesystem type.

Install libfuse on your Distribution once.

```bash
sudo apt install libfuse-dev
```

Mount Repository of fuse.borgfs filesystem type at `<mount point>`.

```bash
sudo mount -r -o allow_other -t fuse.borgfs /var/borg/repo.borg/ <mount point>
```

## Thanks

Borg developers' GitHub page.

- @borgbackup https://github.com/borgbackup/borg

@ThomasWaldmann's feedback that using BORG_xxxxxx env variable name risks collisions to BorgBackup.

- https://github.com/ThomasWaldmann
