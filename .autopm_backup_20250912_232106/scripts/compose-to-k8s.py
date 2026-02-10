#!/usr/bin/env python3

"""
Convert Docker Compose configurations to Kubernetes manifests
Specifically designed for Speecher project's CI/CD needs
"""

import yaml
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List

def convert_service_to_deployment(name: str, service: Dict[str, Any], namespace: str = "default") -> Dict[str, Any]:
    """Convert Docker Compose service to Kubernetes Deployment"""
    
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": name,
            "namespace": namespace,
            "labels": {
                "app": name
            }
        },
        "spec": {
            "replicas": 1,
            "selector": {
                "matchLabels": {
                    "app": name
                }
            },
            "template": {
                "metadata": {
                    "labels": {
                        "app": name
                    }
                },
                "spec": {
                    "containers": [{
                        "name": name,
                        "image": service.get("image", f"{name}:latest"),
                        "ports": []
                    }]
                }
            }
        }
    }
    
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    
    # Handle ports
    if "ports" in service:
        for port_mapping in service["ports"]:
            if ":" in port_mapping:
                host_port, container_port = port_mapping.split(":")
                container["ports"].append({
                    "containerPort": int(container_port),
                    "name": f"port-{container_port}"
                })
    
    # Handle environment variables
    if "environment" in service:
        container["env"] = []
        env_vars = service["environment"]
        if isinstance(env_vars, list):
            for env_var in env_vars:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    container["env"].append({"name": key, "value": value})
        elif isinstance(env_vars, dict):
            for key, value in env_vars.items():
                container["env"].append({"name": key, "value": str(value)})
    
    # Handle volumes (simplified)
    if "volumes" in service:
        container["volumeMounts"] = []
        deployment["spec"]["template"]["spec"]["volumes"] = []
        
        for volume in service["volumes"]:
            if ":" in volume:
                host_path, container_path = volume.split(":", 1)
                volume_name = f"vol-{len(container['volumeMounts'])}"
                
                container["volumeMounts"].append({
                    "name": volume_name,
                    "mountPath": container_path.split(":")[0]  # Remove :ro suffix if present
                })
                
                deployment["spec"]["template"]["spec"]["volumes"].append({
                    "name": volume_name,
                    "hostPath": {
                        "path": host_path
                    }
                })
    
    # Handle healthcheck
    if "healthcheck" in service:
        healthcheck = service["healthcheck"]
        if "test" in healthcheck:
            test_cmd = healthcheck["test"]
            if isinstance(test_cmd, list) and test_cmd[0] == "CMD":
                container["livenessProbe"] = {
                    "exec": {
                        "command": test_cmd[1:]
                    },
                    "initialDelaySeconds": 30,
                    "periodSeconds": 10
                }
    
    return deployment

def convert_service_to_k8s_service(name: str, service: Dict[str, Any], namespace: str = "default") -> Dict[str, Any]:
    """Convert Docker Compose service to Kubernetes Service"""
    
    k8s_service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": name,
            "namespace": namespace
        },
        "spec": {
            "type": "ClusterIP",
            "selector": {
                "app": name
            },
            "ports": []
        }
    }
    
    # Handle ports
    if "ports" in service:
        for port_mapping in service["ports"]:
            if ":" in port_mapping:
                host_port, container_port = port_mapping.split(":")
                k8s_service["spec"]["ports"].append({
                    "port": int(host_port),
                    "targetPort": int(container_port),
                    "name": f"port-{container_port}"
                })
    
    return k8s_service

def create_configmap(name: str, data: Dict[str, Any], namespace: str = "default") -> Dict[str, Any]:
    """Create a ConfigMap for environment variables"""
    return {
        "apiVersion": "v1",
        "kind": "ConfigMap", 
        "metadata": {
            "name": f"{name}-config",
            "namespace": namespace
        },
        "data": data
    }

def convert_compose_to_k8s(compose_file: Path, namespace: str = "default") -> List[Dict[str, Any]]:
    """Convert entire Docker Compose file to Kubernetes manifests"""
    
    with open(compose_file, 'r') as f:
        compose_data = yaml.safe_load(f)
    
    manifests = []
    
    # Create namespace
    manifests.append({
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": namespace
        }
    })
    
    # Process services
    services = compose_data.get("services", {})
    
    for service_name, service_config in services.items():
        # Skip profiles that aren't for CI
        if "profiles" in service_config:
            continue
            
        # Create Deployment
        deployment = convert_service_to_deployment(service_name, service_config, namespace)
        manifests.append(deployment)
        
        # Create Service if ports are exposed
        if "ports" in service_config:
            k8s_service = convert_service_to_k8s_service(service_name, service_config, namespace)
            manifests.append(k8s_service)
        
        # Create ConfigMap for environment variables
        if "environment" in service_config:
            env_vars = service_config["environment"]
            config_data = {}
            
            if isinstance(env_vars, dict):
                config_data = {k: str(v) for k, v in env_vars.items()}
            elif isinstance(env_vars, list):
                for env_var in env_vars:
                    if "=" in env_var:
                        key, value = env_var.split("=", 1)
                        config_data[key] = value
            
            if config_data:
                configmap = create_configmap(service_name, config_data, namespace)
                manifests.append(configmap)
    
    return manifests

def main():
    parser = argparse.ArgumentParser(description="Convert Docker Compose to Kubernetes manifests")
    parser.add_argument("compose_file", help="Path to docker-compose.yml file")
    parser.add_argument("-n", "--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    
    args = parser.parse_args()
    
    compose_path = Path(args.compose_file)
    if not compose_path.exists():
        print(f"Error: {compose_path} does not exist")
        sys.exit(1)
    
    try:
        manifests = convert_compose_to_k8s(compose_path, args.namespace)
        
        # Output manifests
        output_yaml = ""
        for i, manifest in enumerate(manifests):
            if i > 0:
                output_yaml += "---\n"
            output_yaml += yaml.dump(manifest, default_flow_style=False)
            output_yaml += "\n"
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output_yaml)
            print(f"Kubernetes manifests written to {args.output}")
        else:
            print(output_yaml)
            
    except Exception as e:
        print(f"Error converting compose file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()