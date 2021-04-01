import datetime
import docker
from docker.types import LogConfig
import json
import os
from packaging import version

class FoundryInstance(object):

    @classmethod
    def Create(cls, foundry, name, version, port):
        path = os.path.join(foundry.instances_path, name)
        data_path = os.path.join(path, "data")
        bin_path = os.path.join(path, "bin")
        if not os.path.exists(path):
            os.system(f"mkdir -p {path}")
            os.system(f"mkdir -p {data_path}")
            os.system(f"mkdir -p {bin_path}")
            instance = FoundryInstance(foundry, name, version, port)
            instance.write_settings()
            return instance
        return cls.Load(foundry, name)

    @classmethod
    def Load(cls, foundry, name):
        return FoundryInstance(foundry, name)
 
    def __init__(self, foundry, name, version="", port=30000):
        self._foundry = foundry
        self._name = name
        self._version = version
        self._port = port
        self._service = f"{self._foundry.docker_image}-{self._name}"
        self._create_date = datetime.datetime.now()
        self._path = os.path.join(foundry.instances_path, self._name)
        self._bin_path = os.path.join(self._path, "bin")
        self._instance_data_path = os.path.join(self._path, "data")
        self._data_path = os.path.join(self._instance_data_path, "Data")
        self._config_path = os.path.join(self._instance_data_path, "Config")
        self._logs_path = os.path.join(self._instance_data_path, "Logs")
        self._worlds_path = os.path.join(self._data_path, "worlds")
        self._settings_path = os.path.join(self.path, "settings.db")
        self.load_settings()
        self._dclient = docker.client.from_env()

    @property
    def path(self):
        return self._path

    @property
    def instance_data_path(self):
        return self._instance_data_path

    @property
    def world_path(self):
        return self._worlds_path
    
    @property
    def name(self):
        return self._name
    
    @property
    def version(self):
        return self._version
    
    @property
    def service(self):
        return self._service
    
    @property
    def create_date(self):
        return self._create_date
    
    @property
    def port(self):
        return self._port
    
    def create_service(self):
        if not self._get_service():
            lc = LogConfig(type=LogConfig.types.JSON, config={"max-size": "10m", "max-file": "3", "labels": "production_status", "env": "os,customer"})
            service = self._dclient.containers.create(
                f"{self._foundry.docker_image}:{str(self._version)}",
                tty=True,
                restart_policy={"Name": "unless-stopped"},
                name=f"foundryvtt-{self._name}",
                detach=True,
                stdin_open=True,
                ports={'30000/tcp': self._port},
                log_config=lc,
                volumes={self._instance_data_path: {'bind': '/home/foundry/data', 'mode': 'rw'}})
            service.start()
    
    def start(self):
        service = self._get_service()
        if not service:
            self.create_service()
            service = self._get_service()
        service.start()
        
    def stop(self):
        service = self._get_service()
        if not service:
            self.create_service()
            service = self._get_service()
        service.stop()
    
    def status(self):
        service = self._get_service()
        return service.status
    
    def logs(self):
        service = self._get_service()
        return service.logs().decode()

    def full_backup(self):
        self._foundry.backup_manager.create_full_backup(self)
    
    def world_backup(self):
        self._foundry.backup_manager.create_world_backup(self)

    def load_settings(self):
        try:
            with open(self._settings_path, "rt") as f:
                info = json.load(f)
                self._version = version.parse(info["version"])
                self._service = info["service"]
                self._create_date = datetime.datetime.strptime(info["create_date"], "%Y-%m-%dT%H:%M:%S.%f")
        except Exception as e:
            print(f"Cannot load settings: {e}")

    def write_settings(self):
        info = {
            "name": self._name,
            "version": str(self._version),
            "service": self._service,
            "create_date": self._create_date.isoformat(),
            }
        
        with open(self._settings_path, "wt") as f:
            json.dump(info, f)
    
    def _get_service(self):
        try:
            container = self._dclient.containers.get(self._service)
            return container
        except Exception:
            return None


    def __str__(self):
        return f"Name: {self.name} Version: {self.version} Service: {self.service} Port: {self.port} Creation: {self.create_date}"
    
    def __repr__(self):
        return f"Name: {self.name} Version: {self.version} Service: {self.service} Port: {self.port} Creation: {self.create_date}"
