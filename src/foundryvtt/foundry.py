import datetime
import docker
import json
import os
import psutil
import re
import requests
import subprocess

from packaging import version
from .instance import FoundryInstance
from .backupmgr import BackupManager

class FoundryRepo(object):

    def __init__(self, path="/etc/foundryvtt.repo"):
        self._path = path
        self._instances = []
        self.load()
    
    @property
    def instances(self):
        return self._instances
    
    @property
    def main(self):
        if self._instances:
            return self._instances[0]
        return None

    def add(self, instance: FoundryInstance):
        if instance.path not in self._instances_paths:
            self._instances.append(instance)
            self.write()

    @property
    def _instances_paths(self):
        return [i.path for i in self._instances]

    def load(self):
        try:
            with open(self._path, "rt") as f:
                repo = json.load(f)
                for r in repo["instances"]:
                    self.add(Foundry.Load(r))
        except Exception as e:
            print(f"Cannot load repo: {e}")

    def write(self):
        repo = {
            "instances": self._instances_paths,
            }
        
        with open(self._path, "wt") as f:
            json.dump(repo, f)
        
class Foundry(object):

    @classmethod
    def Create(cls, path: str="/var/storage/foundryvtt", backup: str="backup", instances: str="instances", production_instance: str="prod", production_version: str="0.7.9", docker_image: str="foundryvtt"):
        #Create foundry repo
        if not os.path.exists(path):
            os.system(f"mkdir -p {path}")
            
            #Create backup folder
            os.system(f'mkdir -p {os.path.join(path, backup)}')

            #Create instances folder
            os.system(f'mkdir -p {os.path.join(path, instances)}')

            #Create prod instance
            obj = Foundry(path, backup, instances, production_instance, docker_image)
            obj.write_settings()
            obj.create_instance(production_instance, production_version)
            return obj

        return cls.Load(path)
    
    @classmethod
    def Load(cls, path: str="/var/storage/foundryvtt"):
        return Foundry(path)

    def __init__(self, path: str="/var/storage/foundryvtt", backup: str="backup", instances: str="instances", production_instance: str="prod", docker_image: str="foundryvtt"):
        self._path = path
        self._backup = backup
        self._instances = instances
        self._production_instance = production_instance
        self._docker_image = docker_image
        self._backup_path = os.path.join(self._path, self._backup)
        self._instances_path = os.path.join(self._path, self._instances)
        self._production_instance_path = os.path.join(self._instances_path, self._production_instance)
        self._settings_path = os.path.join(self.path, "settings.db")
        self.load_settings()
        self._backup_manager = BackupManager.Load(self)

    @property
    def path(self):
        return self._path
    
    @property
    def backup_path(self):
        return self._backup_path
    
    @property
    def backup_manager(self):
        return self._backup_manager
    
    @property
    def instances_path(self):
        return self._instances_path

    @property
    def production_instance(self):
        return self._production_instance
    
    @property
    def docker_image(self):
        return self._docker_image

    def get_instances(self):
        instances = []
        for name in os.listdir(self._instances_path):
            instance = FoundryInstance.Load(self, name)
            instances.append(instance)
        return instances
    
    def get_instance(self, name: str):
        return FoundryInstance.Load(self, name)

    def create_instance(self, name: str, version: str=""):
        if not version:
            version = self.get_versions()[0]
        return FoundryInstance.Create(self, name, version, self.get_available_port())
    
    def clean_world_backup(self, keep_delta: datetime.timedelta=datetime.timedelta(30), old_count: int=0):
        self.backup_manager.cleanup_world(keep_delta, old_count)
    
    def clean_full_backup(self, keep_delta: datetime.timedelta=datetime.timedelta(30), old_count: int=0):
        self.backup_manager.cleanup_full(keep_delta, old_count)
    
    def get_versions(self):
        dclient = docker.client.from_env()
        images = dclient.images.list(self._docker_image)
        versions = []
        for image in images:
            for tag in image.tags:
                v = re.findall(f"{self._docker_image}:(.*)", tag)
                if v:
                    versions.append(version.parse(v[0]))
        return sorted(versions, reverse=True)

    def get_listening_ports(self):
        connections = psutil.net_connections(kind='tcp4')
        ports = []
        for c in connections:
            if c.status == "LISTEN":
                if c.laddr.port not in ports:
                    ports.append(c.laddr.port)
        instances = self.get_instances()
        for instance in instances:
            if instance.port not in ports:
                ports.append(instance.port)
        return sorted(ports)

    def get_available_port(self):
        ports = self.get_listening_ports()
        port = 30000
        while port < 40000:
            if port not in ports:
                return port
            port += 1
        return -1
   
    def get_connections(self):
        try:
            connections = []
            res = subprocess.getoutput("ss -o state established '( sport = :http or sport = :https )'")
            ips = []
            for l in res.split("\n")[1:]:
                parts = re.findall(r"tcp\s+(\d+)\s+(\d+)\s+([^\s]+)\s+([^\s]+)\s+", l)
                ip, _ = parts[0][3].split(":")
                if ip not in ips:
                    ips.append(ip)
            i = 1
            for ip in ips:
                res = requests.get(f"https://ipinfo.io/{ip}")
                info = res.json()
                connections.append({"ip": ip, "city": info["city"], "region": info["region"], "country": info["country"], "org": info["org"], "postal": info["postal"]})
                i += 1
            return connections
        except Exception as e:
            print("Cannot get connections", e)
            return []

    def load_settings(self):
        try:
            with open(self._settings_path, "rt") as f:
                info = json.load(f)
                self._backup = info["backup"]
                self._instances = info["instances"]
                self._production_instance = info["production_instance"]
                self._docker_image = info["docker_image"]
                self._backup_path = os.path.join(self._path, self._backup)
                self._instances_path = os.path.join(self._path, self._instances)
                self._production_instance_path = os.path.join(self._instances_path, self._production_instance)
        except Exception as e:
            print(f"Cannot load settings: {e}")

    def write_settings(self):
        info = {
            "backup": self._backup,
            "instances": self._instances,
            "production_instance": self._production_instance,
            "docker_image": self._docker_image,
            }
        
        with open(self._settings_path, "wt") as f:
            json.dump(info, f)
        
    def __str__(self):
        return f"Path: {self.path}"
    
    def __repr__(self):
        return f"Path: {self.path}"