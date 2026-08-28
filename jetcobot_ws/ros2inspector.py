#!/usr/bin/env python3

import subprocess
import os
from pathlib import Path
from datetime import datetime

# =====================================================
# CHANGE THIS PATH
# =====================================================
OUTPUT_DIR = "/home/aturki/Desktop/ROS_Documentation"
# =====================================================

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def run(command):
    """Run shell command and return stdout."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        return str(e)


def save(filename, content):
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Saved: {filepath}")


print("\nCollecting ROS information...\n")

# -----------------------------------------------------
# Timestamp
# -----------------------------------------------------

save(
    "timestamp.txt",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

# -----------------------------------------------------
# Environment
# -----------------------------------------------------

save("ros_version.txt", run("ros2 doctor"))

save("environment.txt", run("env"))

# -----------------------------------------------------
# Nodes
# -----------------------------------------------------

nodes = run("ros2 node list")
save("nodes.txt", nodes)

node_list = [n.strip() for n in nodes.splitlines() if n.strip()]

# -----------------------------------------------------
# Topics
# -----------------------------------------------------

save("topics.txt", run("ros2 topic list"))

save("topics_with_types.txt", run("ros2 topic list -t"))

# -----------------------------------------------------
# Services
# -----------------------------------------------------

save("services.txt", run("ros2 service list"))

# -----------------------------------------------------
# Actions
# -----------------------------------------------------

save("actions.txt", run("ros2 action list"))

# -----------------------------------------------------
# Parameters
# -----------------------------------------------------

parameter_output = ""

for node in node_list:
    parameter_output += "=" * 80 + "\n"
    parameter_output += node + "\n\n"
    parameter_output += run(f"ros2 param list {node}")
    parameter_output += "\n\n"

save("parameters.txt", parameter_output)

# -----------------------------------------------------
# Node Information
# -----------------------------------------------------

node_info = ""

for node in node_list:
    node_info += "=" * 80 + "\n"
    node_info += node + "\n\n"
    node_info += run(f"ros2 node info {node}")
    node_info += "\n\n"

save("node_info.txt", node_info)

# -----------------------------------------------------
# Topic Information
# -----------------------------------------------------

topics = run("ros2 topic list").splitlines()

topic_info = ""

for topic in topics:

    topic = topic.strip()

    if topic == "":
        continue

    topic_info += "=" * 80 + "\n"
    topic_info += topic + "\n\n"
    topic_info += run(f"ros2 topic info {topic}")
    topic_info += "\n"

save("topic_info.txt", topic_info)

# -----------------------------------------------------
# Topic Interfaces
# -----------------------------------------------------

interfaces = ""

typed_topics = run("ros2 topic list -t").splitlines()

for line in typed_topics:

    if "[" not in line:
        continue

    topic = line.split()[0]
    msg_type = line.split("[")[-1].replace("]", "").strip()

    interfaces += "=" * 80 + "\n"
    interfaces += topic + "\n"
    interfaces += msg_type + "\n\n"

    interfaces += run(f"ros2 interface show {msg_type}")
    interfaces += "\n\n"

save("interfaces.txt", interfaces)

print("\nDone!")
print(f"\nEverything saved into:\n{OUTPUT_DIR}")