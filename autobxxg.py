#!/usr/bin/env python3

# Copyright (c) 2021 Patineboot. All rights reserved.
# autobxxg software is licensed under BSD 2-Clause license.
"""
BSD 2-Clause License

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from typing import Final

import os
import sys
import subprocess
import logging
from logging.handlers import RotatingFileHandler
from logging import Logger


#############
# Configure #
#############
#
# The Logical Volumes which autobxxg backups
# Note: LVM logical volumes. Pick up from the output of `lvdisplay` and `df -T` commands.
LOGICAL_VOLUMES: Final[tuple] = (
    # LV Path,                 filesystem type
    ("/dev/ubuntu-vg/archive", "ext4"),
    ("/dev/ubuntu-vg/ubuntu-lv", "ext4"),
)

#
# The path to BorgBackup repository.
#
BXXG_REPOSITORY: Final[str] = "/var/borg/repo.borg"

#
# The file including only BorgBackup passphrase.
#
BXXG_PASS_PHRASE: Final[str] = ".borg-passphrase"

#
# The numbers of keeping latest archives related to times when autobxxg prunes.
# WARNING: More earlier archives are removed from the repository.
BXXG_PRUNE_KEEP_NUMBERS: Final[dict] = {
    "--keep-secondly": 0,
    "--keep-minutely": 0,
    "--keep-hourly": 24,
    "--keep-daily": 31,
    "--keep-weekly": 104,
    "--keep-monthly": 0,
    "--keep-yearly": 0,
}

#
# The patterns that autobxxg excludes files from backup archives.
# Note: If the patterns is absolute path, autobxxg will combine
#       the mount point to lvm snapshot with the absolute path.
BXXG_EXCLUDE_PATTERNS: Final[tuple] = (
    "/tmp",
    "/var/cache",
    "/var/tmp",
    "/swap.img",
    "/root/.cache",
    "/home/*/.cache",
)

# The archive prefix and postfix with which combine archive name.
BXXG_ARCHIVE_PREFIX: Final[str] = "{hostname}-"
BXXG_ARCHIVE_POSTFIX: Final[str] = "-{now}"

######################
# Advanced Configure #
######################
DEBUG_DRY_RUN: Final[bool] = False
LOGGER: Final[Logger] = logging.getLogger(__name__)
LOGGER_LOG_LEVEL: Final[int] = logging.INFO
LOGGER_LOG_FILENAME: Final[str] = "/var/log/autobxxg.log"

# The base directory where autobxxg mounts lvm snapshot.
MOUNT_BASE_DIRECTORY: Final[str] = "/"

# The snapshot postfix with which autobxxg combine LV Name.
SNAPSHOT_POSTFIX: Final[str] = "-jxy"

#
# Linux Commands
#

# Pass str.format with the following command and variables.
# str.format replace "{}" in the command to variables.

# Replace `{}` to mount path of snapshot LV.
MKDIR: Final[str] = "mkdir -p {}"
# Replace `{}` to mount path of snapshot LV.
RMDIR: Final[str] = "rmdir {}"

# Replace 1st `{}` to snapshot LV Name, 2nd `{}` LV Path of backup.
LVCREATE_SNAPSHOT: Final[str] = "lvcreate -s -l 100%FREE -n {} {}"
# Replace `{}` to mount path of snapshot LV.
LVREMOVE: Final[str] = "lvremove -f {}"

# Replace 1st `{}` to filesystem type, 2nd `{}` to snapshot LV Path, 3rd `{}` to mount path of snapshot LV.
MOUNT: Final[str] = "mount -r -t {} {} {}"
# Replace `{}` to mount path of snapshot LV.
UMOUNT: Final[str] = "umount -f {}"


def mount_snapshot(snapshot_lvname, mount_dir, lvpath, fs_type):
    """Create lvm snapshot from logocal volume and mount the snapshot on the path to directory.
    Args:
        snapshot_lvname: The name of lvm snapshot which this function create.
        mount_dir: The path to directory where this function mounts lvm snapshot.
        lvpath: The logical volume which is backuped.
        fs_type: The filesystem type of the logical volume.
    """

    LOGGER.debug("STR: {} {} {} {}".format(snapshot_lvname, mount_dir, lvpath, fs_type))

    device_path = os.path.dirname(lvpath)
    snapshot_lvpath = os.path.join(device_path, snapshot_lvname)

    mkdir_str = MKDIR.format(mount_dir)
    run_command(mkdir_str)

    lvcreate_str = LVCREATE_SNAPSHOT.format(snapshot_lvname, lvpath)
    run_command(lvcreate_str)

    mount_str = MOUNT.format(fs_type, snapshot_lvpath, mount_dir)
    run_command(mount_str)

    LOGGER.debug("END")


def backup_snapshot(archive_name, mount_dir):
    """Backup the path to directory.
    Args:
        archive_name: The archive name which identifies backup archive created.
        mount_dir: The path to directory where this function backups.
    """

    LOGGER.debug("STR: {} {}".format(archive_name, mount_dir))

    BXXG_CREATE =               \
        "borg create "          \
        "--verbose "            \
        "--filter AME "         \
        "--list "               \
        "--stats "              \
        "--show-rc "            \
        "--compression lz4 "    \
        "--one-file-system "    \
        "--exclude-caches "
    BXXG_OPTIONAL_EXCLUDE = "--exclude"

    create_str = BXXG_CREATE
    create_str += " "

    for pattern in BXXG_EXCLUDE_PATTERNS:
        if os.path.isabs(pattern):
            # combine mount path and pattern if pattern is absolute
            pattern = os.path.join(mount_dir, pattern[1:])
        create_str += BXXG_OPTIONAL_EXCLUDE + " " + pattern
        create_str += " "

    archive = BXXG_REPOSITORY + "::" + BXXG_ARCHIVE_PREFIX + archive_name + BXXG_ARCHIVE_POSTFIX
    create_str += archive
    create_str += " "

    create_str += mount_dir
    create_str += " "
    run_command(create_str)

    LOGGER.debug("END")


def tear_down(snapshot_lvpath, umount_dir):
    """Unmount the path to directory and remove lvm snapshot.
    Args:
        snapshot_lvpath: The path of lvm snapshot which mount_snapshot() function created.
        umount_dir: The path to directory where mount_snapshot() function mount.
    """

    LOGGER.debug(": {} {}".format(snapshot_lvpath, umount_dir))

    umount_str = UMOUNT.format(snapshot_lvpath)
    run_command(umount_str, False)

    lvremove_str = LVREMOVE.format(snapshot_lvpath)
    run_command(lvremove_str, False)

    rmdir_str = RMDIR.format(umount_dir)
    run_command(rmdir_str, False)

    LOGGER.debug("END")


def prune_archives(archive_name):
    """Prune archives of the repository.
    Args:
        archive_name: The archive name which identifies backup archive created.
    """

    LOGGER.debug("STR: {}".format(archive_name))

    BXXG_PRUNE =        \
        "borg prune "   \
        "--list "       \
        "--show-rc "
    BXXG_OPTIONAL_PREFIX = "--prefix"

    prune_str = BXXG_PRUNE
    prune_str += " "

    for k, v in BXXG_PRUNE_KEEP_NUMBERS.items():
        prune_str += k + " " + str(v)
        prune_str += " "

    archive_prefix = BXXG_ARCHIVE_PREFIX + archive_name
    prune_str += BXXG_OPTIONAL_PREFIX + " " + archive_prefix
    prune_str += " "

    prune_str += BXXG_REPOSITORY
    prune_str += " "

    run_command(prune_str)

    LOGGER.debug("END")


def logging_last_archives(count):
    """Print information of the archives backuped last.
    Args:
        count: The count of the archives backuped last.
    """

    LOGGER.debug("STR: {}".format(count))

    BXXG_INFO =         \
        "borg info "    \
        "--last "

    info_str = BXXG_INFO
    info_str += " "

    info_str += str(count)
    info_str += " "

    info_str += BXXG_REPOSITORY
    info_str += " "

    run_command(info_str, logging=True)

    LOGGER.debug("END")


def run_command(command_line, check=True, logging=False):
    """Run the command.
    Args:
        command_line: The command line containing command and options.
        check: if True, raise exception if command returns error code.
        logging: if True, log return code and stdout/stderr of the command on log level INFO.
    """

    LOGGER.info("CL: {}".format(command_line))
    if DEBUG_DRY_RUN:
        return

    command = command_line.split()
    process = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if process.returncode != 0:
        LOGGER.error("command line: {}".format(command))
        LOGGER.error("error code: {}".format(process.returncode))
        LOGGER.error("error message: {}".format(process.stdout))
        if check:
            process.check_returncode()

    if logging:
        LOGGER.info("CL returncode and stdout/stderr: {}\n{}".format(process.returncode, process.stdout))


def backup_logical_volumes(backup=True):
    """Start to backup the Logical volumes and tear down.
    """

    LOGGER.debug("STR: {}".format(backup))

    # Start to backup the Logical volumes.
    for volume in LOGICAL_VOLUMES:
        lvname = os.path.basename(volume[0])
        snapshot_lvname = lvname + SNAPSHOT_POSTFIX
        device_path = os.path.dirname(volume[0])
        snapshot_lvpath = os.path.join(device_path, snapshot_lvname)

        mount_dir = os.path.join(MOUNT_BASE_DIRECTORY, snapshot_lvname)

        if backup:
            # create and mount snapshot
            mount_snapshot(snapshot_lvname, mount_dir, volume[0], volume[1])

            # backup snapshot mounted
            backup_snapshot(lvname, mount_dir)

        # tear down
        tear_down(snapshot_lvpath, mount_dir)

    LOGGER.debug("END")


def start_backup():
    """Start to backup the Logical volumes and prune archives of the repository.
    """

    LOGGER.debug("STR")

    # Get password from passphrase files in the directory of this script file.
    base_dir = os.path.dirname(__file__)
    passphrase_file = os.path.join(base_dir, BXXG_PASS_PHRASE)
    with open(passphrase_file, mode="r") as passphrase:
        os.environ["BORG_PASSPHRASE"] = passphrase.read()

    # Start to backup the Logical volumes.
    backup_logical_volumes(True)

    # Prune archives of the repository.
    for volume in LOGICAL_VOLUMES:
        lvname = os.path.basename(volume[0])
        # prune archives of the repository
        prune_archives(lvname)

    # info the backup archives of the repository.
    logging_last_archives(len(LOGICAL_VOLUMES))

    LOGGER.debug("END")


if __name__ == "__main__":

    # Initialize logger
    LOGGER.setLevel(LOGGER_LOG_LEVEL)
    format = logging.Formatter("[%(asctime)s][%(levelname)-5.5s][%(name)s]%(filename)s:%(lineno)d %(funcName)s: %(message)s")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(format)
    LOGGER.addHandler(stdout_handler)

    logfile_handler = RotatingFileHandler(LOGGER_LOG_FILENAME, maxBytes=(1048576 * 5), backupCount=2)
    logfile_handler.setFormatter(format)
    LOGGER.addHandler(logfile_handler)

    LOGGER.debug("LOG START")

    try:
        # Start backup
        start_backup()
    except BaseException:
        # tear down if exception occur
        backup_logical_volumes(False)
        raise

    LOGGER.debug("LOG END")
