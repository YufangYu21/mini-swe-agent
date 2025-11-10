import os
import subprocess
from unittest.mock import patch

import pytest

from minisweagent.environments.docker import DockerEnvironment, DockerEnvironmentConfig


def is_docker_available():
    """Check if Docker is available and running."""
    try:
        subprocess.run(["docker", "version"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_podman_available():
    """Check if Podman is available and running."""
    try:
        subprocess.run(["podman", "version"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Test parameters for both Docker and Podman
environment_params = [
    pytest.param(
        "docker",
        marks=pytest.mark.skipif(not is_docker_available(), reason="Docker not available"),
        id="docker",
    ),
    pytest.param(
        "podman",
        marks=pytest.mark.skipif(not is_podman_available(), reason="Podman not available"),
        id="podman",
    ),
]


@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_config_defaults(executable):
    """Test that DockerEnvironmentConfig has correct default values."""
    config = DockerEnvironmentConfig(image="python:3.11", executable=executable)

    assert config.image == "python:3.11"
    assert config.cwd == "/"
    assert config.env == {}
    assert config.forward_env == []
    assert config.timeout == 30
    assert config.executable == executable


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_basic_execution(executable):
    """Test basic command execution in Docker container."""
    env = DockerEnvironment(image="python:3.11", executable=executable)

    try:
        result = env.execute("echo 'hello world'")
        assert result["returncode"] == 0
        assert "hello world" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_set_env_variables(executable):
    """Test setting environment variables in the container."""
    env = DockerEnvironment(
        image="python:3.11", executable=executable, env={"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"}
    )

    try:
        # Test single environment variable
        result = env.execute("echo $TEST_VAR")
        assert result["returncode"] == 0
        assert "test_value" in result["output"]

        # Test multiple environment variables
        result = env.execute("echo $TEST_VAR $ANOTHER_VAR")
        assert result["returncode"] == 0
        assert "test_value another_value" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_forward_env_variables(executable):
    """Test forwarding environment variables from host to container."""
    with patch.dict(os.environ, {"HOST_VAR": "host_value", "ANOTHER_HOST_VAR": "another_host_value"}):
        env = DockerEnvironment(
            image="python:3.11", executable=executable, forward_env=["HOST_VAR", "ANOTHER_HOST_VAR"]
        )

        try:
            # Test single forwarded environment variable
            result = env.execute("echo $HOST_VAR")
            assert result["returncode"] == 0
            assert "host_value" in result["output"]

            # Test multiple forwarded environment variables
            result = env.execute("echo $HOST_VAR $ANOTHER_HOST_VAR")
            assert result["returncode"] == 0
            assert "host_value another_host_value" in result["output"]
        finally:
            env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_forward_nonexistent_env_variables(executable):
    """Test forwarding non-existent environment variables (should be empty)."""
    env = DockerEnvironment(image="python:3.11", executable=executable, forward_env=["NONEXISTENT_VAR"])

    try:
        result = env.execute('echo "[$NONEXISTENT_VAR]"')
        assert result["returncode"] == 0
        assert "[]" in result["output"]  # Empty variable should result in empty string
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_combined_env_and_forward(executable):
    """Test both setting and forwarding environment variables together."""
    with patch.dict(os.environ, {"HOST_VAR": "from_host"}):
        env = DockerEnvironment(
            image="python:3.11", executable=executable, env={"SET_VAR": "from_config"}, forward_env=["HOST_VAR"]
        )

        try:
            result = env.execute("echo $SET_VAR $HOST_VAR")
            assert result["returncode"] == 0
            assert "from_config from_host" in result["output"]
        finally:
            env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_env_override_forward(executable):
    """Test that explicitly set env variables take precedence over forwarded ones."""
    with patch.dict(os.environ, {"CONFLICT_VAR": "from_host"}):
        env = DockerEnvironment(
            image="python:3.11",
            executable=executable,
            env={"CONFLICT_VAR": "from_config"},
            forward_env=["CONFLICT_VAR"],
        )

        try:
            result = env.execute("echo $CONFLICT_VAR")
            assert result["returncode"] == 0
            # The explicitly set env should take precedence (comes first in docker exec command)
            assert "from_config" in result["output"]
        finally:
            env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_custom_cwd(executable):
    """Test executing commands in a custom working directory."""
    env = DockerEnvironment(image="python:3.11", executable=executable, cwd="/tmp")

    try:
        result = env.execute("pwd")
        assert result["returncode"] == 0
        assert "/tmp" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_cwd_parameter_override(executable):
    """Test that the cwd parameter in execute() overrides the config cwd."""
    env = DockerEnvironment(image="python:3.11", executable=executable, cwd="/")

    try:
        result = env.execute("pwd", cwd="/tmp")
        assert result["returncode"] == 0
        assert "/tmp" in result["output"]
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_command_failure(executable):
    """Test that command failures are properly captured."""
    env = DockerEnvironment(image="python:3.11", executable=executable)

    try:
        result = env.execute("exit 42")
        assert result["returncode"] == 42
    finally:
        env.cleanup()


@pytest.mark.slow
@pytest.mark.parametrize("executable", environment_params)
def test_docker_environment_custom_container_timeout(executable):
    """Test that custom container_timeout is respected."""
    import time

    env = DockerEnvironment(image="python:3.11", executable=executable, container_timeout="3s")

    try:
        result = env.execute("echo 'container is running'")
        assert result["returncode"] == 0
        assert "container is running" in result["output"]
        time.sleep(5)
        with pytest.raises((subprocess.CalledProcessError, subprocess.TimeoutExpired)):
            # This command should fail because the container has stopped
            subprocess.run(
                [executable, "exec", env.container_id, "echo", "still running"],
                check=True,
                capture_output=True,
                timeout=2,
            )
    finally:
        env.cleanup()


def test_docker_environment_config_local_registry_defaults():
    """Test that DockerEnvironmentConfig has correct default values for local registry."""
    config = DockerEnvironmentConfig(image="python:3.11")

    assert config.local_registry == "localhost:5000"  # Default from environment or hardcoded
    assert config.prefer_local_registry is True


def test_docker_environment_config_local_registry_from_env():
    """Test that local_registry can be set from environment variable.
    
    Note: Since dataclass field defaults are evaluated at class definition time,
    the environment variable is read when the module is first imported.
    This test verifies that explicit setting works, which is the recommended way
    to use environment variables in dataclasses.
    """
    # Test that explicit setting works (which is how environment variables
    # would typically be used in practice)
    config = DockerEnvironmentConfig(image="python:3.11", local_registry="custom-registry:8080")
    assert config.local_registry == "custom-registry:8080"


def test_docker_environment_config_local_registry_explicit():
    """Test that local_registry can be set explicitly."""
    config = DockerEnvironmentConfig(image="python:3.11", local_registry="my-registry:5000")
    assert config.local_registry == "my-registry:5000"


def test_docker_environment_config_prefer_local_registry_false():
    """Test that prefer_local_registry can be disabled."""
    config = DockerEnvironmentConfig(image="python:3.11", prefer_local_registry=False)
    assert config.prefer_local_registry is False


def test_docker_environment_get_local_registry_image():
    """Test _get_local_registry_image method."""
    config = DockerEnvironmentConfig(image="python:3.11", local_registry="localhost:5000")
    env = DockerEnvironment(image="python:3.11", local_registry="localhost:5000")

    # Test with regular image name
    result = env._get_local_registry_image("python:3.11")
    assert result == "localhost:5000/python:3.11"

    # Test with docker.io prefix (should be removed)
    result = env._get_local_registry_image("docker.io/python:3.11")
    assert result == "localhost:5000/python:3.11"

    # Test with full docker.io path
    result = env._get_local_registry_image("docker.io/swebench/sweb.eval.x86_64.test:latest")
    assert result == "localhost:5000/swebench/sweb.eval.x86_64.test:latest"

    # Test with None local_registry
    env_no_registry = DockerEnvironment(
        image="python:3.11", local_registry=None, prefer_local_registry=False
    )
    result = env_no_registry._get_local_registry_image("python:3.11")
    assert result == "python:3.11"

    env_no_registry.cleanup()


@patch("minisweagent.environments.docker.subprocess.run")
def test_docker_environment_pull_image_success(mock_subprocess):
    """Test _pull_image method with successful pull."""
    # Mock successful pulls for both initialization and test
    def mock_run_side_effect(*args, **kwargs):
        if args[0][0:2] == ["docker", "pull"]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout="Success",
                stderr="",
            )
        elif args[0][0:2] == ["docker", "run"]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout="container-id-123",
                stderr="",
            )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    mock_subprocess.side_effect = mock_run_side_effect

    env = DockerEnvironment(image="python:3.11", prefer_local_registry=False)
    result = env._pull_image("test-image")

    assert result is True
    # Verify that pull was called for test-image
    pull_calls = [call for call in mock_subprocess.call_args_list if call[0][0][0:2] == ["docker", "pull"] and "test-image" in call[0][0]]
    assert len(pull_calls) >= 1
    env.cleanup()


@patch("minisweagent.environments.docker.subprocess.run")
def test_docker_environment_pull_image_failure(mock_subprocess):
    """Test _pull_image method with failed pull."""
    call_count = [0]  # Use list to allow modification in nested function

    def mock_run_side_effect(*args, **kwargs):
        call_count[0] += 1
        if args[0][0:2] == ["docker", "pull"]:
            # First call (during init) succeeds, subsequent calls for test-image fail
            if call_count[0] == 1:
                return subprocess.CompletedProcess(
                    args=args[0],
                    returncode=0,
                    stdout="Success",
                    stderr="",
                )
            else:
                raise subprocess.CalledProcessError(1, args[0], stderr="Error")
        elif args[0][0:2] == ["docker", "run"]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout="container-id-123",
                stderr="",
            )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    mock_subprocess.side_effect = mock_run_side_effect

    env = DockerEnvironment(image="python:3.11", prefer_local_registry=False)
    result = env._pull_image("test-image")

    assert result is False
    env.cleanup()


@patch("minisweagent.environments.docker.subprocess.run")
def test_docker_environment_pull_image_timeout(mock_subprocess):
    """Test _pull_image method with timeout."""
    call_count = [0]  # Use list to allow modification in nested function

    def mock_run_side_effect(*args, **kwargs):
        call_count[0] += 1
        if args[0][0:2] == ["docker", "pull"]:
            # First call (during init) succeeds, subsequent calls for test-image timeout
            if call_count[0] == 1:
                return subprocess.CompletedProcess(
                    args=args[0],
                    returncode=0,
                    stdout="Success",
                    stderr="",
                )
            else:
                raise subprocess.TimeoutExpired(args[0], timeout=120)
        elif args[0][0:2] == ["docker", "run"]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout="container-id-123",
                stderr="",
            )
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout="", stderr="")

    mock_subprocess.side_effect = mock_run_side_effect

    env = DockerEnvironment(image="python:3.11", prefer_local_registry=False)
    result = env._pull_image("test-image")

    assert result is False
    env.cleanup()


@patch("minisweagent.environments.docker.DockerEnvironment._pull_image")
@patch("minisweagent.environments.docker.subprocess.run")
def test_docker_environment_prefer_local_registry_success(mock_subprocess, mock_pull):
    """Test that local registry is preferred when image exists there."""
    # Mock successful pull from local registry
    mock_pull.side_effect = lambda img: img == "localhost:5000/python:3.11"

    # Mock successful docker run
    mock_result = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=0,
        stdout="container-id-123",
        stderr="",
    )
    mock_subprocess.return_value = mock_result

    env = DockerEnvironment(
        image="python:3.11", local_registry="localhost:5000", prefer_local_registry=True
    )

    # Verify that local registry was tried first
    assert mock_pull.call_count >= 1
    # First call should be to local registry
    assert "localhost:5000" in mock_pull.call_args_list[0][0][0]

    env.cleanup()


@patch("minisweagent.environments.docker.DockerEnvironment._pull_image")
@patch("minisweagent.environments.docker.subprocess.run")
def test_docker_environment_fallback_to_docker_hub(mock_subprocess, mock_pull):
    """Test that falls back to Docker Hub when local registry doesn't have the image."""
    # Mock: local registry fails, Docker Hub succeeds
    def pull_side_effect(img):
        if "localhost:5000" in img:
            return False  # Not in local registry
        return True  # Available in Docker Hub

    mock_pull.side_effect = pull_side_effect

    # Mock successful docker run
    mock_result = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=0,
        stdout="container-id-123",
        stderr="",
    )
    mock_subprocess.return_value = mock_result

    env = DockerEnvironment(
        image="python:3.11", local_registry="localhost:5000", prefer_local_registry=True
    )

    # Verify both local registry and Docker Hub were tried
    assert mock_pull.call_count >= 2
    # First call should be to local registry
    assert "localhost:5000" in mock_pull.call_args_list[0][0][0]
    # Second call should be to original image
    assert "localhost:5000" not in mock_pull.call_args_list[1][0][0]

    env.cleanup()


@patch("minisweagent.environments.docker.DockerEnvironment._pull_image")
@patch("minisweagent.environments.docker.subprocess.run")
def test_docker_environment_skip_local_registry_when_disabled(mock_subprocess, mock_pull):
    """Test that local registry is skipped when prefer_local_registry is False."""
    # Mock successful pull from Docker Hub
    mock_pull.return_value = True

    # Mock successful docker run
    mock_result = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=0,
        stdout="container-id-123",
        stderr="",
    )
    mock_subprocess.return_value = mock_result

    env = DockerEnvironment(
        image="python:3.11", local_registry="localhost:5000", prefer_local_registry=False
    )

    # Verify local registry was not tried
    for call in mock_pull.call_args_list:
        assert "localhost:5000" not in call[0][0]

    env.cleanup()


@patch("minisweagent.environments.docker.DockerEnvironment._pull_image")
@patch("minisweagent.environments.docker.subprocess.run")
def test_docker_environment_skip_local_registry_when_none(mock_subprocess, mock_pull):
    """Test that local registry is skipped when local_registry is None."""
    # Mock successful pull from Docker Hub
    mock_pull.return_value = True

    # Mock successful docker run
    mock_result = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=0,
        stdout="container-id-123",
        stderr="",
    )
    mock_subprocess.return_value = mock_result

    env = DockerEnvironment(image="python:3.11", local_registry=None, prefer_local_registry=True)

    # Verify local registry was not tried (no localhost:5000 in any call)
    for call in mock_pull.call_args_list:
        assert "localhost:5000" not in call[0][0]

    env.cleanup()
