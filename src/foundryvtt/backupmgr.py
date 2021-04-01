import datetime
import os
import re
from .backup import Backup


class BackupManager(object):
    
    @classmethod
    def Load(cls, foundry):
        return BackupManager(foundry)

    def __init__(self, foundry):
        self._foundry = foundry

    @property
    def backup_path(self):
        return self._foundry.backup_path

    def get_backups(self):
        worlds = []
        fulls = []

        for file in os.listdir(self.backup_path):
            if re.match(r"(\w+)-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})\.zip", file):
                backup_info = re.findall(r"(\w+)-(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})\.zip", file)
                date_parts = (int(x) for x in backup_info[0][1:])
                backup_type = backup_info[0][0]
                date = datetime.datetime(*date_parts)
                backup = Backup(self.backup_path, file, date)
                if backup_type == "world":
                    worlds.append(backup)
                else:
                    fulls.append(backup)
        worlds = sorted(worlds, key = lambda i: i.date, reverse=True)
        fulls = sorted(fulls, key = lambda i: i.date, reverse=True)
        return worlds, fulls

    def get_full_backups(self):
        _, fulls = self.get_backups()
        return fulls

    def get_world_backups(self):
        worlds, _ = self.get_backups()
        return worlds

    def generate_backup_name(self, prefix, instance):
        now = datetime.datetime.now()
        return f"{prefix}-{now.strftime('%Y%m%d-%H%M%S')}"

    def create_backup_folder(self, backup_dir):
        os.system(f"mkdir -p {self.backup_path}/{backup_dir}")

    def create_full_backup(self, instance):
        backup_dir = self.generate_backup_name("full", instance)
        self.create_backup_folder(backup_dir)

        os.system(f"rsync -a --progress {instance.instance_data_path}/ {self.backup_path}/{backup_dir}")
        os.system(f"cd {self.backup_path}/ && zip -r {backup_dir}.zip ./{backup_dir}")
        os.system(f"rm -rf {self.backup_path}/{backup_dir}")

    def create_world_backup(self, instance):
        backup_dir = self.generate_backup_name("world", instance)
        self.create_backup_folder(backup_dir)

        os.system(f"mkdir -p {self.backup_path}/{backup_dir}/Data")
        os.system(f"rsync -a --progress {instance.instance_data_path}/Data/worlds {self.backup_path}/{backup_dir}/Data")
        os.system(f"rsync -a --progress {instance.instance_data_path}/Data/assets {self.backup_path}/{backup_dir}/Data")
        os.system(f"cd {self.backup_path}/ && zip -r {backup_dir}.zip ./{backup_dir}")
        os.system(f"rm -rf {self.backup_path}/{backup_dir}")

    def restore_full_backup(self, backup, instance):
        src_tmp_path = instance.instance_data_path + ".bak"
        backup_file = f'{self.backup_path}/{backup.file}'
        tmp_path = f"{self.backup_path}/restore-full"

        print(f"Create unzip dir {tmp_path}")
        os.system(f"mkdir -p {tmp_path}")
        print(f"Unzip backup {backup_file} to {tmp_path}")
        os.system(f"unzip {backup_file} -d {tmp_path}")
        print(f"Rename data dir {instance.instance_data_path} to {src_tmp_path}")
        os.system(f"mv {instance.instance_data_path} {src_tmp_path}")
        print(f"Copy backup {tmp_path} to data path {instance.instance_data_path}")
        os.system(f"rsync -a --progress {tmp_path}/{backup.name}/ {instance.instance_data_path}")
        os.system(f"rm -rf {src_tmp_path}")
        os.system(f"rm -rf {tmp_path}")
    
    def restore_world_backup(self, backup, instance):
        src_tmp_path = instance.instance_data_path + ".bak"
        backup_file = f'{self.backup_path}/{backup.file}'
        tmp_path = f"{self.backup_path}/restore-world"

        print(f"Create unzip dir {tmp_path}")
        os.system(f"mkdir -p {tmp_path}")
        print(f"Unzip backup {backup_file} to {tmp_path}")
        os.system(f"unzip {backup_file} -d {tmp_path}")
        print(f"Copy data dir {instance.instance_data_path} to {src_tmp_path}")
        os.system(f"rsync -a --progress {instance.instance_data_path}/ {src_tmp_path}")
        print(f"Copy backup {tmp_path} to data path {instance.world_path}")
        os.system(f"rsync -a --progress {tmp_path}/{backup.name}/ {instance.instance_data_path}")
        # os.system(f"rm -rf {src_tmp_path}")
        # os.system(f"rm -rf {tmp_path}")
