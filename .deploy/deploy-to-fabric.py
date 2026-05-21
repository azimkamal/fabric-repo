import os, argparse, requests, ast
from fabric_cicd import (
    FabricWorkspace,
    publish_all_items,
    unpublish_all_orphan_items,
    change_log_level,
)
from azure.identity import ClientSecretCredential
 
def get_workspace_id(p_ws_name, p_token):
    url = "https://api.fabric.microsoft.com/v1/workspaces"
    headers = {
        "Authorization": f"Bearer {p_token.token}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        for workspace in response.json()["value"]:
            if workspace["displayName"] == p_ws_name:
                return workspace["id"]
        return f"Error: Workspace {p_ws_name} could not be found."
    return f"Error: {response.status_code}, {response.text}"
 
change_log_level("DEBUG")
 
parser = argparse.ArgumentParser()
parser.add_argument('--aztenantid',    type=str)
parser.add_argument('--azclientid',    type=str)
parser.add_argument('--azspsecret',    type=str)
parser.add_argument('--target_env',    type=str)
parser.add_argument('--items_in_scope',type=str)
args = parser.parse_args()
 
token_credential = ClientSecretCredential(
    client_id=args.azclientid,
    client_secret=args.azspsecret,
    tenant_id=args.aztenantid,
)
 
# Resolve workspace name from GitHub Variable
# e.g. target_env='test' → reads TEST_WORKSPACE_NAME env var
tgtenv = args.target_env
ws_name_var = f"{tgtenv.upper()}_WORKSPACE_NAME"
workspace_name = os.environ[ws_name_var]
 
resource = 'https://api.fabric.microsoft.com/'
scope = f'{resource}.default'
token = token_credential.get_token(scope)
 
lookup_response = get_workspace_id(workspace_name, token)
if isinstance(lookup_response, str) and lookup_response.startswith("Error"):
    raise ValueError(f"{lookup_response}. Check workspace name in GitHub Variables.")
wks_id = lookup_response
 
repository_directory = os.environ['GIT_DIRECTORY']
item_types = ast.literal_eval(args.items_in_scope)
 
target_workspace = FabricWorkspace(
    workspace_id=wks_id,
    environment=tgtenv,
    repository_directory=repository_directory,
    item_type_in_scope=item_types,
    token_credential=token_credential,
)
 
publish_all_items(target_workspace)
unpublish_all_orphan_items(target_workspace)
print("Deployment complete.")
