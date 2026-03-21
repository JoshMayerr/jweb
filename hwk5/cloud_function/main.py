import os

from googleapiclient.discovery import build


def stop_cloud_sql(request):
    project_id = os.environ["PROJECT_ID"]
    instance_name = os.environ["INSTANCE_NAME"]

    service = build("sqladmin", "v1beta4", cache_discovery=False)
    instance = (
        service.instances()
        .get(project=project_id, instance=instance_name)
        .execute()
    )
    current_state = instance.get("state", "UNKNOWN")
    if current_state == "RUNNABLE":
        service.instances().stop(project=project_id, instance=instance_name).execute()
        return {"status": "stopping", "instance": instance_name}, 200
    return {"status": "already-stopped", "instance": instance_name, "state": current_state}, 200
