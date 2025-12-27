"""
Enhanced Sandbox Templates for Full-Stack Development

Multi-language sandboxes with package managers and network access.
Agent can now install packages, build websites, develop complete systems.
"""

# Enhanced Docker images with package managers
ENHANCED_SANDBOX_IMAGES = {
    # Python development with pip
    "python_dev": {
        "image": "python:3.11-slim",
        "packages": ["pip", "virtualenv"],
        "network": True,  # Can install packages
        "description": "Python development with pip package manager"
    },
    
    # Node.js development with npm/yarn
    "nodejs_dev": {
        "image": "node:18-alpine",
        "packages": ["npm", "yarn"],
        "network": True,
        "description": "Node.js development with npm/yarn"
    },
    
    # Full-stack web development
    "fullstack_web": {
        "image": "ubuntu:22.04",
        "packages": ["python3", "pip", "nodejs", "npm", "git", "curl"],
        "network": True,
        "description": "Full-stack: Python + Node.js + system tools"
    },
    
    # System development with build tools
    "system_dev": {
        "image": "ubuntu:22.04",
        "packages": ["build-essential", "gcc", "make", "git"],
        "network": True,
        "description": "C/C++ system development"
    },
    
    # Data science with common libs
    "datascience": {
        "image": "python:3.11",
        "packages": ["pandas", "numpy", "scipy", "scikit-learn"],
        "network": True,
        "description": "Data science with pre-installed libraries"
    },
}


# Dockerfile templates for custom sandboxes
DOCKERFILE_TEMPLATES = {
    "fullstack_web": """
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-venv \\
    nodejs \\
    npm \\
    git \\
    curl \\
    wget \\
    && rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /workspace
RUN chmod 777 /workspace

# Non-root user
RUN useradd -m -s /bin/bash developer
USER developer

CMD ["bash"]
""",

    "python_ml": """
FROM python:3.11-slim

# Install ML libraries
RUN pip install --no-cache-dir \\
    numpy \\
    pandas \\
    scikit-learn \\
    matplotlib \\
    jupyter

WORKDIR /workspace
USER nobody
CMD ["python3"]
""",

    "web_server": """
FROM node:18-alpine

# Install common web frameworks
RUN npm install -g \\
    express \\
    react \\
    next \\
    @nestjs/cli

WORKDIR /workspace
USER node
CMD ["node"]
"""
}


# Agent can now request these capabilities
AGENT_CAPABILITIES = {
    "install_package": {
        "python": "pip install {package}",
        "nodejs": "npm install {package}",
        "system": "apt-get install -y {package}"
    },
    
    "create_project": {
        "react": "npx create-react-app {name}",
        "nextjs": "npx create-next-app {name}",
        "django": "django-admin startproject {name}",
        "flask": "flask init {name}"
    },
    
    "run_server": {
        "python": "python3 -m http.server {port}",
        "nodejs": "npx http-server -p {port}",
        "flask": "flask run --host=0.0.0.0 --port={port}",
        "django": "python manage.py runserver 0.0.0.0:{port}"
    }
}


def get_capability_code(capability: str, language: str, **kwargs) -> str:
    """
    Generate code for common development tasks.
    
    Agent can use this to:
    - Install packages
    - Create new projects
    - Run web servers
    - Build systems
    """
    if capability in AGENT_CAPABILITIES:
        template = AGENT_CAPABILITIES[capability].get(language)
        if template:
            return template.format(**kwargs)
    return None
