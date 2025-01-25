#!/usr/bin/python3
from datetime import datetime
import logging
import sys
import os
import subprocess
import shutil


"""
Todo: 
DONE: Provide exclude files/dirs in config file.
DONE: Robust logging including into backup destin dir.
DONE: Create and store tar locally in tmp dir then move it to dest dir.
Mulitple destintations in config file for duplicate backups. (Chanlenge will be to have these pruned as well).
"""


logger = logging.getLogger(__name__)
logging.basicConfig(filename='tmp_dragonfly_backup.log', encoding='utf-8', level=logging.DEBUG, format='%(asctime)s: %(levelname)s %(message)s')

temp_dir_name = ".df_tmp_bc"

def _clean_lines(lines, str_ix, end_ix, set_space_dir_file=False):
    logger.info(f"_clean_lines:: start: {str_ix}, end: {end_ix} ")
    r_list = []
    for i in range(str_ix+1, end_ix):
        if len(lines[i]) > 0:
            if lines[i][0] != '#':
                line = lines[i]
                if '#' in line:
                    line = line[:(line.find('#'))]
                new_l = line.replace('"', '')
                if (set_space_dir_file==False): # Do this for source files with -C flag
                    path_, file_ = os.path.split(new_l)
                    new_l = f"{path_} {file_}"
                r_list.append(new_l)
    return r_list



def backup_logger(backup_vars, log_str, log_level="info"):
    """Previously log was writtten to DEST once it was set up. Now, it is wrtten into temp dir so it is available immeaditly"""
    log_file = backup_vars["TEMP_PATH_LOG_NAME"]
    now = datetime.now()
    date_stamp =  now.strftime('%Y/%m/%d %H:%M:%S')
    log_str_formatted = f"[{date_stamp}] {log_level.upper()}: {log_str}\n"
    with open(log_file, 'a') as lf:
        lf.write(log_str_formatted)
    return


def parse_config_file(cf_file, backup_vars, debug=False):
    if not os.path.isfile(cf_file):
        logger.error(f"parse_config_file:: config file {cf_file} not found.")
        exit(1)
    else:
        with open(cf_file) as cf:
            cf_lines = cf.read().splitlines()
        src_line_nr = -1
        dst_line_nr = -1
        exc_line_nr = -1
        max_keep = 10
        for ix, l in enumerate(cf_lines):
            if "MAX_KEEP" in l:
                max_keep = int(l.split('=')[-1])
            if "BACKUP_SRC" in l or "BACKUP_SOURCE" in l:
                src_line_nr = ix
            if "BACKUP_DST" in l or "BACKUP_DESTINATION" in l:
                dst_line_nr = ix
            if "BACKUP_EXC" in l or "BACKUP_EXCLUSION" in l:
                exc_line_nr = ix
        if (src_line_nr == -1 or dst_line_nr == -1):
            e_m = f"parse_config_file:: syntax error in {cf_file}"
            logger.error(e_m)
            print(e_m)
            return None
        if (exc_line_nr == -1):
            exc_line_nr = dst_line_nr
        if not (src_line_nr < dst_line_nr) and not (src_line_nr < exc_line_nr):
            e_m = f"parse_config_file:: syntax error in {cf_file}, order of 'BACKUP_SRC', 'BACKUP_EXC' and 'BACKUP_DST' is incorrect."
            logger.error(e_m)
            print(e_m)
            return None

        backup_source_list = _clean_lines(cf_lines, src_line_nr, exc_line_nr, set_space_dir_file=False)
        if exc_line_nr < dst_line_nr:
            backup_excl_list   = _clean_lines(cf_lines, exc_line_nr, dst_line_nr, set_space_dir_file=True)
        else:
            backup_excl_list   = []
        backup_dest_list   = _clean_lines(cf_lines, dst_line_nr, len(cf_lines), set_space_dir_file=True)

        backup_vars["SOURCE_LIST"] = backup_source_list
        #backup_vars["DESTINATION"] = backup_dest.replace('"', '')
        backup_vars["DESTINATION"] = backup_dest_list[0] # Only allow one destination for now.
        backup_vars["DESTINATION_LIST"] = backup_dest_list # Only allow one destination for now.
        backup_vars["EXCLUSION_LIST"] = backup_excl_list 
        backup_vars["MAX_KEEP"] = max_keep 
        return backup_vars


def set_backup_backup_variables(backup_vars, debug=False):
    backup_vars["TEMP_PATH"] = os.path.join(os.getcwd(), temp_dir_name)
    #dest_dir = backup_vars["DESTINATION_PATH"]
    #        os.makedirs(os.path.join(current_dir, ".df_tmp_bc"))
    now = datetime.now()
    date_stamp =  now.strftime('%Y%m%d%H%M%S')
    backup_vars["DATE"] = date_stamp
    backup_vars["TAR_NAME"] = f"backup_{date_stamp}.tar" 
    backup_vars["DESTINATION_PATH"] = os.path.join(backup_vars["DESTINATION"], date_stamp)
    backup_vars["PATH_TAR_NAME"] = os.path.join(backup_vars["DESTINATION_PATH"], f"backup_{date_stamp}.tar" )
    backup_vars["LOG_NAME"] = f"backup_{date_stamp}.log"
    backup_vars["PATH_LOG_NAME"] = os.path.join(backup_vars["DESTINATION_PATH"], f"backup_{date_stamp}.log" )
    backup_vars["TEMP_PATH_TAR_NAME"] = os.path.join(backup_vars["TEMP_PATH"], f"backup_{date_stamp}.tar" )
    backup_vars["TEMP_PATH_LOG_NAME"] = os.path.join(backup_vars["TEMP_PATH"], f"backup_{date_stamp}.log" )
    if (debug==True):
        for c in backup_vars:
            logger.debug(f"{c}: {backup_vars[c]}")
    return backup_vars

def prepare_dir(backup_vars, dry_run=False, debug=False):
    temp_dir = backup_vars["TEMP_PATH"]
    dest_dir = backup_vars["DESTINATION_PATH"]
    if (dry_run==True):
        print(f"prepare_dir:: Backup directory to be created at:\n\t {dest_dir}")
        print(f"prepare_dir:: Backup directory to be created at:\n\t {temp_dir}")
    if (dry_run==False):
        try:
            os.makedirs(dest_dir)
        except FileExistsError:
            logger.warning("Destination path already created.")
        try:
            os.makedirs(temp_dir)
        except FileExistsError:
            logger.warning("Temp path already created.")
    return 0



def tar_it_up(backup_vars, dry_run=False, debug=False):
    cmd = []
    tar_cmd = "tar"
    if (debug==True):
        tar_flag = "-czvf"
    if (debug==False):
        tar_flag = "-czf"
    c_flag = "-C"
    exc_flag = "--exclude"
    #dest = backup_vars["PATH_TAR_NAME"]
    #dest = os.path.join(backup_vars["TEMP_PATH"], backup_vars["TAR_NAME"])
    dest = backup_vars["TEMP_PATH_TAR_NAME"]

    cmd.append(tar_cmd)
    cmd.append(tar_flag)
    cmd.append(dest)

    for f in backup_vars["EXCLUSION_LIST"]:
        path_file_list = f.split('/')
        path_file = path_file_list[-2] +'/'+ path_file_list[-1] # There seems to be no way to get parent path via os.path module so have to do it the hard way.
        cmd.append(f'{exc_flag}={path_file}')
    for f in backup_vars["SOURCE_LIST"]:
        cmd.append(c_flag)
        path_file = f.split(" ")
        cmd.append(path_file[0])
        cmd.append(path_file[1])

    if (debug==True):
        backup_logger(backup_vars, " ".join(cmd), log_level="debug")
        logger.debug(" ".join(cmd))
    if (dry_run==True):
        i_l = "tar_it_up:: dry running command: "
        print(i_l)
        for c in cmd:
            print(c, end=" ")
        print()
    if (dry_run==False):
        process = subprocess.run(cmd, capture_output=True)
        if (len(process.stdout) > 1):
            o_l = f"tar command process output: {process.stdout.decode('utf-8')}."
            logger.info(o_l)
            backup_logger(backup_vars, o_l.rstrip(), log_level="debug")
        if (len(process.stderr) > 1):
            e_l = f"tar command process error: {process.stderr}."
            logger.error(e_l)
            backup_logger(backup_vars, e_l, log_level="error")
            print("e:", process.stderr)
    return 0


def test_tar(backup_vars, dry_run=False, debug=False):
    cmd = []
    tar_cmd = "tar"
    if (debug==True):
        tar_flag = "-tvf"
    if (debug==False):
        tar_flag = "-tf"
    #dest = backup_vars["TEMP_PATH"]
    #dest = os.path.join(backup_vars["TEMP_PATH"], backup_vars["TAR_NAME"])
    dest = backup_vars["TEMP_PATH_TAR_NAME"]
    cmd.append(tar_cmd)
    cmd.append(tar_flag)
    cmd.append(dest)
    if (debug==True):
        backup_logger(backup_vars, " ".join(cmd), log_level="debug")
        logger.debug(" ".join(cmd))
    if (dry_run==True):
        i_l = f"test_tar:: dry running command: {cmd}"
        print(i_l)
        backup_logger(backup_vars, i_l, log_level="debug")
    if (dry_run==False):
        process = subprocess.run(cmd, capture_output=True)
        process_output = process.stdout.decode("utf-8")
        if (len(process.stdout) > 1):
            o_l = f"tar command test process output: {process_output}."
            logger.info(o_l)
            backup_logger(backup_vars, o_l, log_level="info")
        if (len(process.stderr) > 1):
            e_l = f"tar command test process error: {process.stderr}."
            logger.error(e_l)
            print("e:", process.stderr)
            backup_logger(backup_vars, e_l, log_level="error")
        for in_file in backup_vars["SOURCE_LIST"]:
            file_path = in_file.split(" ")
            if file_path[1] not in process_output:
                w_l = f"File {file_path[1]} not contained in tar."
                print(w_l)
                backup_logger(backup_vars, w_l, log_level="warning")

def cat_logs(backup_vars, debug=False):
    cmd = []
    cat_cmd = "cat"
    dir = backup_vars["PATH_LOG_NAME"]
    cmd.append(cat_cmd)
    cmd.append(dir)
    process = subprocess.run(cmd, capture_output=True)
    process_output = process.stdout.decode("utf-8")
    if (len(process.stdout) > 1):
        logger.info(f"cat command test process output: {process_output}.")
    if (len(process.stderr) > 1):
        logger.error(f"cat command test process error: {process.stderr}.")
        print("e:", process.stderr)

def move_tar_to_destination(backup_vars, dry_run=False, debug=False):
    current_dir = backup_vars["TEMP_PATH"]
    #current_tar = os.path.join(current_dir, backup_vars["TAR_NAME"])
    #current_log = os.path.join(current_dir, backup_vars["LOG_NAME"])
    current_tar = backup_vars["TEMP_PATH_TAR_NAME"]
    current_log = backup_vars["TEMP_PATH_LOG_NAME"]
    ultimate_tar = backup_vars["PATH_TAR_NAME"]
    ultimate_log = backup_vars["PATH_LOG_NAME"]
    ultimate_dir = backup_vars["DESTINATION_PATH"]

    m = []
    m.append(f"move_tar_to_destination:: current dir: {current_dir}")
    m.append(f"move_tar_to_destination:: current tar: {current_tar}")
    m.append(f"move_tar_to_destination:: current log: {current_log}")
    m.append(f"move_tar_to_destination:: ultimate tar: {ultimate_tar}")
    m.append(f"move_tar_to_destination:: ultimate log: {ultimate_log}")
    m.append(f"move_tar_to_destination:: ultimate dir: {ultimate_dir}")

    for mm in m:
        logger.debug(mm)
        if (debug==True):
            print(mm)
            backup_logger(backup_vars, mm, log_level="debug")
    if (dry_run==False):
        
        try:
            shutil.move(current_tar, ultimate_dir)
        except (OSError, FileNotFoundError) as e:
            logger.error(f"Move error {e}: '{current_log}' '{ultimate_log}'.")
        try:
            shutil.move(current_log, ultimate_dir)
        except (OSError, FileNotFoundError) as e:
            logger.error(f"Move error {e}: '{current_log}' '{ultimate_log}'.")
    return 0


    


def prune_old_backups(backup_vars, dry_run=False, debug=False):
    max_keep = backup_vars["MAX_KEEP"]
    rm_cmd = "rm"
    rm_flag = "-rf"
    destination_path = backup_vars["DESTINATION"]
    old_backup_list = os.listdir(destination_path)
    old_backup_list.sort(reverse=True)
    file_count_pre = len(old_backup_list)
    old_backup_list = old_backup_list[max_keep:]
    for d_rm in old_backup_list:
        cmd = []
        cmd.append(rm_cmd)
        cmd.append(rm_flag)
        cmd.append(os.path.join(destination_path, d_rm))
        if (dry_run==False):
            process = subprocess.run(cmd)
            new_backup_list = os.listdir(destination_path)
            if (len(new_backup_list) > max_keep):
                e_l = "prune_old_backups:: failure"
                logger.error(e_l)
                backup_logger(backup_vars, e_l, log_level="error")
        if (dry_run==True):
            i_l = f"prune_old_backups:: dry running command: {cmd}"
            print(i_l)
            logger.error(i_l)
            backup_logger(backup_vars, i_l, log_level="debug")
    

if __name__ == "__main__":
    arg_dry_run = False
    arg_debug = False
    arg_test = False
    if ("--dry-run" in sys.argv):
        arg_dry_run = True
    if ("--debug" in sys.argv):
        arg_debug = True
    if ("--test-config" in sys.argv):
        arg_test = True

    if arg_test==True:
        external_config_file = "test_backup.config"
    else:
        external_config_file = "dragonfly_backup.config"
    logger.info(f"Starting script: dry-run: {arg_dry_run}, debug: {arg_debug}.")

    backup_variables = {}
    backup_variables = parse_config_file(external_config_file, backup_variables, debug=arg_debug)
    backup_variables = set_backup_backup_variables(backup_variables, debug=arg_debug)
    prepare_dir(backup_variables, dry_run=arg_dry_run, debug=arg_debug)
    tar_it_up(backup_variables, dry_run=arg_dry_run, debug=arg_debug)
    test_tar(backup_variables, dry_run=arg_dry_run, debug=arg_debug)
    move_tar_to_destination(backup_variables, dry_run=arg_dry_run, debug=arg_debug)
    cat_logs(backup_variables, debug=arg_debug)
    prune_old_backups(backup_variables, dry_run=arg_dry_run)
    m = f"Backup script completed."
    logger.info(m)
    backup_logger(backup_variables, m, log_level="info")

