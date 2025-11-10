import logging
import os
import shlex
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DockerEnvironmentConfig:
    image: str
    cwd: str = "/"
    """Working directory in which to execute commands."""
    env: dict[str, str] = field(default_factory=dict)
    """Environment variables to set in the container."""
    forward_env: list[str] = field(default_factory=list)
    """Environment variables to forward to the container.
    Variables are only forwarded if they are set in the host environment.
    In case of conflict with `env`, the `env` variables take precedence.
    """
    timeout: int = 30
    """Timeout for executing commands in the container."""
    executable: str = os.getenv("MSWEA_DOCKER_EXECUTABLE", "docker")
    """Path to the docker/container executable."""
    run_args: list[str] = field(default_factory=lambda: ["--rm"])
    """Additional arguments to pass to the docker/container executable.
    Default is ["--rm"], which removes the container after it exits.
    """
    container_timeout: str = "2h"
    """Max duration to keep container running. Uses the same format as the sleep command."""
    pull_timeout: int = 600
    """Timeout in seconds for pulling images."""
    local_registry: str | None = os.getenv("MSWEA_LOCAL_REGISTRY", "localhost:5000")
    """Local Docker registry to try first when pulling images. If None, skip local registry."""
    prefer_local_registry: bool = True
    """Whether to prefer local registry over Docker Hub. If True, tries local registry first."""


class DockerEnvironment:
    def __init__(self, *, config_class: type = DockerEnvironmentConfig, logger: logging.Logger | None = None, **kwargs):
        """This class executes bash commands in a Docker container using direct docker commands.
        See `DockerEnvironmentConfig` for keyword arguments.
        """
        self.logger = logger or logging.getLogger("minisweagent.environment")
        self.container_id: str | None = None
        self.config = config_class(**kwargs)
        self._start_container()

    def get_template_vars(self) -> dict[str, Any]:
        return asdict(self.config)

    def _pull_image(self, image_name: str) -> bool:
        """Try to pull an image. Returns True if successful."""
        try:
            cmd = [self.config.executable, "pull", image_name]
            self.logger.debug(f"Pulling image: {shlex.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.pull_timeout,
                check=True,
            )
            self.logger.info(f"Successfully pulled image: {image_name}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.debug(f"Failed to pull image {image_name}: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            self.logger.debug(f"Timeout while pulling image {image_name}")
            return False

    def _get_local_registry_image(self, image_name: str) -> str:
        """Convert image name to local registry format."""
        if self.config.local_registry:
            # Remove docker.io prefix if present
            if image_name.startswith("docker.io/"):
                image_name = image_name[len("docker.io/"):]
            return f"{self.config.local_registry}/{image_name}"
        return image_name

    def _start_container(self):
        """Start the Docker container and return the container ID."""
        image_to_use = self.config.image
        
        # Try to pull from local registry first if enabled
        if self.config.prefer_local_registry and self.config.local_registry:
            local_image = self._get_local_registry_image(self.config.image)
            self.logger.info(f"Attempting to pull from local registry: {local_image}")
            if self._pull_image(local_image):
                image_to_use = local_image
                self.logger.info(f"Using image from local registry: {image_to_use}")
            else:
                self.logger.info(f"Image not found in local registry, falling back to: {self.config.image}")
                # Try to pull from original source
                if not self._pull_image(self.config.image):
                    self.logger.warning(f"Failed to pull image {self.config.image}, docker run will attempt to pull it")
        else:
            # Try to pull from original source
            if not self._pull_image(self.config.image):
                self.logger.warning(f"Failed to pull image {self.config.image}, docker run will attempt to pull it")
        
        container_name = f"minisweagent-{uuid.uuid4().hex[:8]}"
        cmd = [
            self.config.executable,
            "run",
            "-d",
            "--name",
            container_name,
            "-w",
            self.config.cwd,
            *self.config.run_args,
            image_to_use,
            "sleep",
            self.config.container_timeout,
        ]
        self.logger.debug(f"Starting container with command: {shlex.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.pull_timeout,  # docker run might also pull
            check=True,
        )
        self.logger.info(f"Started container {container_name} with ID {result.stdout.strip()}")
        self.container_id = result.stdout.strip()

    def execute(self, command: str, cwd: str = "", *, timeout: int | None = None) -> dict[str, Any]:
        """Execute a command in the Docker container and return the result as a dict."""
        cwd = cwd or self.config.cwd
        assert self.container_id, "Container not started"

        cmd = [self.config.executable, "exec", "-w", cwd]
        for key in self.config.forward_env:
            if (value := os.getenv(key)) is not None:
                cmd.extend(["-e", f"{key}={value}"])
        for key, value in self.config.env.items():
            cmd.extend(["-e", f"{key}={value}"])
        cmd.extend([self.container_id, "bash", "-lc", command])

        result = subprocess.run(
            cmd,
            text=True,
            timeout=timeout or self.config.timeout,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return {"output": result.stdout, "returncode": result.returncode}

    def cleanup(self):
        """Stop and remove the Docker container."""
        if getattr(self, "container_id", None) is not None:  # if init fails early, container_id might not be set
            cmd = f"(timeout 60 {self.config.executable} stop {self.container_id} || {self.config.executable} rm -f {self.container_id}) >/dev/null 2>&1 &"
            subprocess.Popen(cmd, shell=True)

    def __del__(self):
        """Cleanup container when object is destroyed."""
        self.cleanup()
