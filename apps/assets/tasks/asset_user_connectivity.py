# ~*~ coding: utf-8 ~*~

from celery import shared_task
from django.utils.translation import ugettext as _

from common.utils import get_logger, get_object_or_none
from orgs.utils import org_aware_func
from ..models import Asset
from . import const
from .utils import check_asset_can_run_ansible


logger = get_logger(__file__)


__all__ = [
    'test_asset_user_connectivity_util', 'test_asset_users_connectivity_manual',
    'get_test_asset_user_connectivity_tasks',
]


def get_test_asset_user_connectivity_tasks(asset):
    if asset.is_unixlike():
        tasks = const.PING_UNIXLIKE_TASKS
    elif asset.is_windows():
        tasks = const.PING_WINDOWS_TASKS
    else:
        msg = _(
            "The asset {} system platform {} does not "
            "support run Ansible tasks".format(asset.hostname, asset.platform)
        )
        logger.info(msg)
        tasks = []
    return tasks


@org_aware_func("asset_user")
def test_asset_user_connectivity_util(asset_user, task_name, run_as_admin=False):
    """
    :param asset_user: <AuthBook>对象
    :param task_name:
    :param run_as_admin:
    :return:
    """
    from ops.utils import update_or_create_ansible_task

    if not check_asset_can_run_ansible(asset_user.asset):
        return

    tasks = get_test_asset_user_connectivity_tasks(asset_user.asset)
    if not tasks:
        logger.debug("No tasks ")
        return

    args = (task_name,)
    kwargs = {
        'hosts': [asset_user.asset], 'tasks': tasks,
        'options': const.TASK_OPTIONS,
    }
    if run_as_admin:
        kwargs["run_as_admin"] = True
    else:
        kwargs["run_as"] = asset_user.username
    task, created = update_or_create_ansible_task(*args, **kwargs)
    raw, summary = task.run()
    asset_user.set_connectivity(summary)


@shared_task(queue="ansible")
def test_asset_users_connectivity_manual(asset_users, run_as_admin=False):
    """
    :param asset_users: <AuthBook>对象
    """
    for asset_user in asset_users:
        task_name = _("Test asset user connectivity: {}").format(asset_user)
        test_asset_user_connectivity_util(asset_user, task_name, run_as_admin=run_as_admin)


@shared_task(queue="ansible")
def push_asset_user_util(asset_user):
    """
    :param asset_user: <Asset user>对象
    """
    from .push_system_user import push_system_user_util
    if not asset_user.backend.startswith('system_user'):
        logger.error("Asset user is not from system user")
        return
    union_id = asset_user.union_id
    union_id_list = union_id.split('_')
    if len(union_id_list) < 2:
        logger.error("Asset user union id length less than 2")
        return
    system_user_id = union_id_list[0]
    asset_id = union_id_list[1]
    asset = get_object_or_none(Asset, pk=asset_id)
    system_user = None
    if not asset:
        return
    hosts = check_asset_can_run_ansible([asset])
    if asset.is_unixlike:
        pass




