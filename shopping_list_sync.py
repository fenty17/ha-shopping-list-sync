###############################################################################
#
# Sync todoist (thereby Alexa etc) lists with Home Assistant using pyscript
#   https://hacs-pyscript.readthedocs.io
#
# NOTE: This is NOT python, it is pyscript... it may LOOK like python but it's
#       not! (especially around the async/await stuff)
#
# Originally posted by MrLemur.
#  https://community.home-assistant.io/t/sync-your-alexa-todoist-shopping-list-to-the-home-assistant-shopping-list/274277
# Touched up and brought to Github by alexisspencer.
#  https://github.com/alexisspencer/shopping_list_sync
#
###############################################################################


TODOIST_TOKEN = "<your token here>"
TODOIST_PROJECT_ID = "<your project/list ID here>"

import asyncio
import aiohttp
import json

def http_get_json(url, headers):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            assert response.status == 200, f"Unexpected response status: {response.status}"
            response_text = response.text()
    return json.loads(response_text)
    
def http_put(url, headers, body=""):
    status_code = 500
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers = headers, json=body) as response:
            status_code = response.status
    return True if status_code == 204 else False

import aiofiles

def write_json(filename, content):    
    j = json.dumps(content, indent=4)
    #log.warning("Writing: "+ str(j))
    async with aiofiles.open(filename, mode='w') as f:
        await f.write(j)
        await f.flush()

def get_tasks():
    return http_get_json(
       url = f"https://api.todoist.com/rest/v2/tasks?project_id={TODOIST_PROJECT_ID}",
        headers = {"Authorization" : f"Bearer {TODOIST_TOKEN}", "Content-Type" : "application/json"}
    )

def add_task(item):
    return http_put(
        url = "https://api.todoist.com/rest/v2/tasks",
        headers = {"Authorization" : f"Bearer {TODOIST_TOKEN}", "Content-Type" : "application/json"},
        body = {"content" : item, "project_id" : TODOIST_PROJECT_ID}
    )
    
def update_task(id, content):
    return http_put(
        url = f"https://api.todoist.com/rest/v2/tasks/{id}",
        headers = {"Authorization" : f"Bearer {TODOIST_TOKEN}", "Content-Type" : "application/json"},
        body = {"content" : content}
    )

def complete_task(id):
    return http_put(
        url = f"https://api.todoist.com/rest/v2/tasks/{id}/close",
        headers = {"Authorization" : f"Bearer {TODOIST_TOKEN}"}
    )

@service
def sync_shopping_list():
    tasks = []
    imported = get_tasks()
    for item in imported:
        tasks.append({"name" : item["content"], "id" : str(item["id"]), "complete" : item["is_completed"]})
    write_json(filename = "/config/.shopping_list.json", content=tasks)
    hass.data["shopping_list"].async_load()
    event.fire("shopping_list_updated", action="dummy")

@event_trigger('shopping_list_updated')
def update_shopping_list(action=None, item=None):
    #log.warning(f"Shopping list updated event. action={action}, item={str(item)} ")
    if action == "add":
        add_task(item["name"])
        sync_shopping_list()
    elif action == "update" and item["complete"] == False:
        update_task(item["id"],item["name"])
        sync_shopping_list()
    elif action == "update" and item["complete"] == True:
        complete_task(item["id"])
        sync_shopping_list()
