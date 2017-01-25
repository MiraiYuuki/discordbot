import os
import sys
import config
import inspect
from command_object import Command, DefaultModuleContext

LOADING_MODULE = None
LOADED_MODULES = set()
MODULE_CONTEXT_CLASSES = {}
MANAGED_COMMAND_PACKAGE = config.get("bot.commands_package", "commands")
MANAGED_COMMAND_PACKAGE_PATH = os.path.dirname(__import__(MANAGED_COMMAND_PACKAGE).__file__)

ROOT_COMMAND     = Command("")
command          = ROOT_COMMAND.subcommand
register_command = ROOT_COMMAND.register_subcommand
delete_command   = ROOT_COMMAND.delete_subcommand

def localname(name):
    return name[len(MANAGED_COMMAND_PACKAGE) + 1:]

def context_class(cls):
    if not LOADING_MODULE:
        raise RuntimeError("@context_class is only usable inside load_modules.")

    MODULE_CONTEXT_CLASSES[LOADING_MODULE] = cls
    return cls

def get_context_class(modobject):
    return MODULE_CONTEXT_CLASSES.get(modobject.__name__, DefaultModuleContext)

def fq_from_leaf(name):
    return ".".join((MANAGED_COMMAND_PACKAGE, name))

def load_modules():
    for a_file in os.listdir(MANAGED_COMMAND_PACKAGE_PATH):
        modulename = inspect.getmodulename(os.path.join(MANAGED_COMMAND_PACKAGE_PATH, a_file))
        if modulename:
            print("load_modules: importing", modulename)
            load_module(modulename)

def load_module(name):
    global LOADING_MODULE

    fq = fq_from_leaf(name)

    LOADING_MODULE = fq
    mod = getattr(__import__(fq), name)
    LOADED_MODULES.add(mod)

    LOADING_MODULE = None

    return mod

def unload_module(name):
    fq = fq_from_leaf(name)
    package = __import__(MANAGED_COMMAND_PACKAGE)

    # remove its registered commands
    for key in list(ROOT_COMMAND.sub_dispatch_table.keys()):
        if ROOT_COMMAND.sub_dispatch_table[key].provider == fq:
            del ROOT_COMMAND.sub_dispatch_table[key]

    # remove its context class
    try:
        del MODULE_CONTEXT_CLASSES[fq]
    except KeyError:
        pass

    LOADED_MODULES.remove(getattr(package, name))
    delattr(package, name)
    del sys.modules[fq]
