from mcdreforged.api.all import *
from typing import Optional, Union, List, Set

gl_psi = ServerInterface.get_instance().as_plugin_server_interface()


class PermissionRequirements(Serializable):
    gen: int = 3
    next: int = 3
    list: int = 1
    load: int = 3
    remove: int = 3
    autoremove: int = 3
    confirm: int = 3
    abort: int = 3


class KeywordsConfiguration(Serializable):
    saved_world: List[str] = [
        'Saved the game',  # 1.13+
        'Saved the world',  # 1.12-
    ]
    generation_finished: List[str] = [
        'Pre-generating of {dimension} finished, took {time}min'
    ]


class Configuration(Serializable):
    command_prefix: Union[str, List[str]] = ['!!upg', '!!pregen']
    max_slots: int = 10
    default_slots: int = 4
    ignored_files: List[str] = [
        'session.lock'
    ]
    countdown_time: int = 5
    backup_path: str = './pre-generated'
    server_path: str = './server'
    restore_temp_folder: str = 'temp'
    regen_command: Optional[str] = 'uhc regen'
    wait_dimensions: List[str] = [
        'overworld', 'the_nether'
    ]
    world_names: List[str] = [
        'world'
    ]
    keywords: KeywordsConfiguration = KeywordsConfiguration.get_default()
    permission_requirements: PermissionRequirements = PermissionRequirements.get_default()

    @property
    def prefix(self) -> List[str]:
        return list(set(self.command_prefix) if isinstance(self.command_prefix, list) else {self.command_prefix})

    @classmethod
    def load(cls) -> 'Configuration':
        return gl_psi.load_config_simple(default_config=cls.get_default().serialize(), target_class=cls)

    def save(self):
        gl_psi.save_config_simple(self)

    def get_prem(self, cmd: str):
        return self.permission_requirements.serialize().get(cmd, 1)

    def is_file_ignored(self, file_name: str) -> bool:
        for item in self.ignored_files:
            if len(item) > 0:
                if item[0] == '*' and file_name.endswith(item[1:]):
                    return True
                if item[-1] == '*' and file_name.startswith(item[:-1]):
                    return True
                if file_name == item:
                    return True
        return False


config = Configuration.load()
