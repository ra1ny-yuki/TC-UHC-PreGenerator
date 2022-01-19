import json
import os
import shutil
import time
from typing import Dict, Optional, Iterable

from mcdreforged.api.all import *  # \Lazy Import/

from tcuhc_pregen.config import config
from tcuhc_pregen.utils import global_psi, debug_log, rm, cp


SLOT_INFO_FILE = 'info.json'


class SlotInfo(Serializable):
    timestamp: float = 0
    used: bool = False
    comment: str = ''

    def save(self, folder_name: str):
        global_psi.save_config_simple(
            self, file_name=os.path.join(config.backup_path, folder_name, SLOT_INFO_FILE), in_data_folder=False
        )

    @classmethod
    def load(cls, folder_name: str) -> Optional['SlotInfo']:
        folder_path = os.path.join(config.backup_path, folder_name)
        if not os.path.isdir(folder_path):
            return None
        if SLOT_INFO_FILE not in os.listdir(folder_path):
            return None
        try:
            with open(os.path.join(folder_path, SLOT_INFO_FILE), 'r', encoding='UTF-8') as f:
                return SlotInfo.deserialize(json.load(f))
        except:
            return None


class StorageManager:
    def __init__(self):
        self.folder = config.backup_path
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)

    def get_slots_info(self, allow_used: bool = False, reverse: bool = False) -> Dict[str, SlotInfo]:
        slot_dirs = os.listdir(self.folder)
        slots_info: Dict[str, SlotInfo] = {slot: SlotInfo.load(slot) for slot in slot_dirs}
        available_slots_info: Dict[str, SlotInfo] = {}
        for slot_dir, slot_info in slots_info.items():
            if slot_info is None or bool(slot_info.used and not allow_used):
                debug_log(f'Slot info: {slot_info}')
                continue
            available_slots_info[slot_dir] = slot_info
        return {slot_dir: slot_info for slot_dir, slot_info in sorted(
            available_slots_info.items(), key=lambda x: x[1].timestamp, reverse=reverse
        )}

    def auto_remove(self) -> int:
        num = 0
        for slot_dir, slot_info in self.get_slots_info(allow_used=True).items():
            try:
                if slot_info.used:
                    shutil.rmtree(self.slot_dir_path(slot_dir))
                    num += 1
            except:
                pass
        for item in os.listdir(self.folder):
            rm(os.path.join(self.folder, item))
        return num

    def remove_slot(self, slot_name: str):
        slot_path = self.slot_dir_path(slot_name)
        if not os.path.isdir(slot_path):
            raise FileNotFoundError
        shutil.rmtree(slot_path)

    def get_default_slot_name(self):
        now_time = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime())
        target_folder = now_time
        while True:
            if target_folder not in os.listdir(self.folder):
                break
            if not target_folder.endswith(' '):
                target_folder += ' '
            target_folder += '1'
        return target_folder

    def backup(self, world_names: Iterable[str], comment: str = ''):
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder)
        target_slot_dir_name = self.get_default_slot_name()
        target_slot_dir_path = os.path.join(self.folder, target_slot_dir_name)
        if not os.path.isdir(target_slot_dir_path):
            os.makedirs(target_slot_dir_path)
        succeeded = {}
        for item in world_names:
            success = True
            original_path = os.path.join(config.server_path, item)
            world_name = item
            if os.path.exists(original_path):
                target_path = os.path.join(target_slot_dir_path, world_name)
                try:
                    try:
                        cp(original_path, target_path, allow_not_found=False)
                    except:
                        success = False
                except Exception as exc:
                    global_psi.logger.exception(f'Unable to copy file "{world_name}":')
                    success = False
            else:
                debug_log(f'File {world_name}: File is not found')
                success = False
            succeeded[item] = success
        for key, value in succeeded.items():
            debug_log(f'Key "{key}": {value}')

        if any(succeeded.values()):
            slot_info = SlotInfo(timestamp=time.time(), used=False, comment=comment)
            slot_info.save(target_slot_dir_name)
        else:
            shutil.rmtree(target_slot_dir_path)
            raise FileNotFoundError('No world file specified found')

    def get_slot_size(self, slot_name: str):
        dir_ = self.slot_dir_path(slot_name)
        size = 0
        for root, dirs, files in os.walk(dir_):
            size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
        return size

    def slot_dir_path(self, slot_name: str, ignore_exc=False):
        if os.path.isdir(slot_name):
            if os.path.basename(slot_name) not in os.listdir(self.folder) or not equal_path(
                    os.path.dirname(slot_name), self.folder):
                if not ignore_exc:
                    raise FileNotFoundError('This backup slot path is not in backup path')
            return slot_name
        else:
            if not os.path.isdir(os.path.join(self.folder, slot_name)):
                if not ignore_exc:
                    raise FileNotFoundError('Slot folder is not found in backup folder')
                return None
            return os.path.join(self.folder, slot_name)


storage = StorageManager()


def equal_path(path1: str, path2: str):
    return os.path.normpath(os.path.abspath(path1)) == os.path.normpath(os.path.abspath(path2))
