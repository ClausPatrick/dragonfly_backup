import os
import sys
import subprocess

pat_file = "PAT/personal_access_token"
local_dir = "/usr/local/bin/dragonfly_backup"

def update_script_hub():
    if not os.path.exists(local_dir):
        print("Backup directory not found.")
        return
    
    print("Updating script...")
    process = subprocess.run(["git", "-C", local_dir, "pull", repo_url], check=True, capture_output=True)
    if (len(process.stdout) > 1):
        print("o:", process.stdout)
    if (len(process.stderr) > 1):
        print("e:", process.stderr)

    print("Update complete.")


def update_script_lab(pat):
    repo_url = f"https://oauth2:{pat}@gitlab.com/residencyoflaniakea/dragonfly_backup"
    print(repo_url)

    try:
        # Check if the local directory exists
        if not os.path.exists(local_dir):
            print("Backup directory not found. Cloning repository...")
            subprocess.run(["git", "clone", repo_url, local_dir], check=True)
        else:
            print("Updating script from GitLab...")
            subprocess.run(["git", "pull", repo_url], check=True)
        print("Update complete.")

    except subprocess.CalledProcessError as e:
        print(f"Error during update: {e}")


if __name__ == "__main__":
    with open(pat_file, 'r') as p:
        lines = p.readlines()
        pat = (lines[0]).rstrip()
    update_script_lab(pat)
