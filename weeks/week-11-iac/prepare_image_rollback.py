"""
Preparation helper for the Week 11 manual image rollback demo.

This script automates README section 10.2 steps 1 to 8:

- checks that Docker and Minikube are operational
- recreates the temporary manual-image-rollback build context
- builds rollback-old and rollback-new locally
- inspects both images to prove their contents differ
- builds both images inside Minikube

It does not run Terraform and it does not perform the rollback itself.
After it finishes successfully, continue manually from README step 9.

Run from anywhere:
    py -3 weeks/week-11-iac/prepare_image_rollback.py
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

PREP_DIR = SCRIPT_DIR / "manual-image-rollback"
PREP_REQUIREMENTS = PREP_DIR / "requirements.txt"
PREP_DOCKERFILE = PREP_DIR / "Dockerfile"
PREP_APP = PREP_DIR / "app.py"

SOURCE_APP = REPO_ROOT / "weeks" / "week-09-compose" / "docker-compose" / "simple-app" / "app.py"

ROLLBACK_OLD_TAG = "simple-app-gsx:rollback-old"
ROLLBACK_NEW_TAG = "simple-app-gsx:rollback-new"

ORIGINAL_RESPONSE_LINE = '            self._send_text(200, f"{MESSAGE} | Visits: {visits}")'
MODIFIED_RESPONSE_LINE = '            self._send_text(200, f"{MESSAGE} | Visits: {visits} | Image: rollback-new")'
MARKER = "| Image: rollback-new"

DOCKERFILE_CONTENT = textwrap.dedent(
    """\
    FROM python:3.12-alpine

    ENV PYTHONDONTWRITEBYTECODE=1 \\
        PYTHONUNBUFFERED=1 \\
        PORT=5000

    WORKDIR /app

    RUN addgroup -S app && adduser -S app -G app

    COPY requirements.txt ./requirements.txt
    RUN pip install --no-cache-dir -r requirements.txt

    COPY app.py ./app.py
    RUN chown -R app:app /app

    USER app

    EXPOSE 5000

    HEALTHCHECK --interval=30s --timeout=3s \\
      CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

    CMD ["python", "app.py"]
    """
)

REQUIREMENTS_CONTENT = "redis==7.4.0\n"


def divider(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def ok(message: str) -> None:
    print(f"[PASS] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def expected(*lines: str) -> None:
    print("[INFO] Expected results:")
    for line in lines:
        print(f"- {line}")


def run(
    cmd: list[str],
    *,
    cwd: Path = REPO_ROOT,
    timeout: int = 60,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(str(part) for part in cmd)}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
    )

    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}")

    return result


def command_output(cmd: list[str], *, timeout: int = 60) -> str:
    return run(cmd, timeout=timeout).stdout


def docker_daemon_accessible() -> bool:
    result = run(["docker", "version", "--format", "{{.Server.Version}}"], check=False, timeout=20)
    return result.returncode == 0 and bool(result.stdout.strip())


def minikube_running() -> bool:
    result = run(["minikube", "status"], check=False, timeout=20)
    status_output = f"{result.stdout}\n{result.stderr}"
    return (
        result.returncode == 0
        and "host: Running" in status_output
        and "apiserver: Running" in status_output
    )


def cluster_accessible() -> bool:
    result = run(["kubectl", "cluster-info"], check=False, timeout=20)
    return result.returncode == 0


def current_context() -> str:
    result = run(["kubectl", "config", "current-context"], check=False, timeout=20)
    if result.returncode != 0:
        return "<unknown>"
    return result.stdout.strip() or "<unknown>"


def ensure_prerequisites() -> None:
    divider("PREREQUISITES")
    expected(
        "docker CLI is available",
        "Docker daemon is reachable",
        "Minikube is installed and its control plane is running",
        "kubectl can reach the active Kubernetes API server",
    )

    run(["docker", "--version"], timeout=20)
    ok("docker CLI is available")

    if docker_daemon_accessible():
        ok("Docker daemon is reachable")
    else:
        raise RuntimeError("Docker daemon is not reachable")

    run(["minikube", "version"], timeout=20)
    ok("minikube CLI is available")

    if minikube_running():
        ok("Minikube control plane is running")
    else:
        raise RuntimeError("Minikube is not operational. Start it before running this script.")

    context = current_context()
    if context == "minikube":
        ok("kubectl current context is minikube")
    else:
        raise RuntimeError(f"kubectl current context is {context!r}, expected 'minikube'")

    if cluster_accessible():
        ok("Kubernetes API is reachable through kubectl")
    else:
        raise RuntimeError("kubectl cannot reach the Kubernetes API")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_file_with_expected_content(path: Path, content: str, description: str) -> None:
    """Create a file when missing, otherwise keep the existing file in place."""
    if path.exists():
        actual = path.read_text(encoding="utf-8")
        if actual == content:
            ok(f"{description} already exists with the expected content")
        else:
            warn(
                f"{description} already exists with different content; "
                "keeping the existing file and skipping regeneration"
            )
        return

    write_file(path, content)
    actual = path.read_text(encoding="utf-8")
    if actual != content:
        raise RuntimeError(f"{description} was created but its content does not match the expected value")
    ok(f"{description} was missing and has been created")


def prepare_step_1() -> None:
    divider("STEP 1: CREATE TEMPORARY BUILD FOLDER")
    expected("the folder weeks/week-11-iac/manual-image-rollback/ exists")
    if PREP_DIR.exists():
        ok(f"Temporary build folder already exists at {PREP_DIR}")
    else:
        PREP_DIR.mkdir(parents=True, exist_ok=True)
        ok(f"Temporary build folder has been created at {PREP_DIR}")


def prepare_step_2() -> None:
    divider("STEP 2: CREATE requirements.txt")
    expected("requirements.txt contains redis==7.4.0")
    ensure_file_with_expected_content(
        PREP_REQUIREMENTS,
        REQUIREMENTS_CONTENT,
        str(PREP_REQUIREMENTS.relative_to(REPO_ROOT)),
    )


def prepare_step_3() -> None:
    divider("STEP 3: CREATE Dockerfile")
    expected("Dockerfile matches the rollback preparation instructions from the README")
    ensure_file_with_expected_content(
        PREP_DOCKERFILE,
        DOCKERFILE_CONTENT,
        str(PREP_DOCKERFILE.relative_to(REPO_ROOT)),
    )


def prepare_step_4() -> None:
    divider("STEP 4: COPY ORIGINAL BACKEND SOURCE")
    expected("manual-image-rollback/app.py starts from the original backend source file")
    source_app = SOURCE_APP.read_text(encoding="utf-8")
    if PREP_APP.exists():
        if PREP_APP.read_text(encoding="utf-8") == source_app:
            ok(f"{PREP_APP.relative_to(REPO_ROOT)} already exists with the original backend source")
        else:
            warn(
                f"{PREP_APP.relative_to(REPO_ROOT)} already exists with different content; "
                "keeping the existing file and skipping the copy step"
            )
        return

    write_file(PREP_APP, source_app)
    actual = PREP_APP.read_text(encoding="utf-8")
    if actual != source_app:
        raise RuntimeError("app.py was created but does not match the original backend source")
    ok(f"Copied {SOURCE_APP.relative_to(REPO_ROOT)} to {PREP_APP.relative_to(REPO_ROOT)}")


def prepare_step_5() -> None:
    divider("STEP 5: ADD THE rollback-new MARKER")
    expected("manual-image-rollback/app.py returns '| Image: rollback-new' on the root endpoint")
    app_source = PREP_APP.read_text(encoding="utf-8")

    if MARKER in app_source:
        ok(f"{PREP_APP.relative_to(REPO_ROOT)} already contains the rollback marker")
        return

    if ORIGINAL_RESPONSE_LINE not in app_source:
        raise RuntimeError(
            "Could not find the original backend response line to modify in manual-image-rollback/app.py. "
            "Delete the file if you want the script to recreate it from scratch."
        )

    modified = app_source.replace(ORIGINAL_RESPONSE_LINE, MODIFIED_RESPONSE_LINE, 1)
    write_file(PREP_APP, modified)

    if MARKER not in PREP_APP.read_text(encoding="utf-8"):
        raise RuntimeError("The rollback marker was not added to app.py")

    ok(f"Modified {PREP_APP.relative_to(REPO_ROOT)} to include {MARKER!r}")


def prepare_step_6() -> None:
    divider("STEP 6: BUILD THE LOCAL IMAGES")
    expected(
        "both docker builds finish without error",
        "docker images simple-app-gsx lists at least rollback-old and rollback-new",
    )

    run(
        [
            "docker",
            "build",
            "-t",
            ROLLBACK_OLD_TAG,
            "-f",
            "weeks/week-11-iac/docker/simple-app.Dockerfile",
            ".",
        ],
        timeout=600,
    )
    ok(f"Built {ROLLBACK_OLD_TAG} locally with Docker")

    run(
        [
            "docker",
            "build",
            "-t",
            ROLLBACK_NEW_TAG,
            "weeks/week-11-iac/manual-image-rollback",
        ],
        timeout=600,
    )
    ok(f"Built {ROLLBACK_NEW_TAG} locally with Docker")

    images_output = command_output(["docker", "images", "simple-app-gsx"], timeout=30)
    if "rollback-old" not in images_output or "rollback-new" not in images_output:
        raise RuntimeError("docker images output does not show both rollback tags")
    ok("docker images simple-app-gsx lists rollback-old and rollback-new")


def prepare_step_7() -> None:
    divider("STEP 7: INSPECT THE IMAGE CONTENTS")
    expected(
        "rollback-old does not contain the marker '| Image: rollback-new'",
        "rollback-new does contain the marker '| Image: rollback-new'",
    )

    rollback_old_source = command_output(
        ["docker", "run", "--rm", ROLLBACK_OLD_TAG, "cat", "/app/app.py"],
        timeout=60,
    )
    if MARKER in rollback_old_source:
        raise RuntimeError(f"{ROLLBACK_OLD_TAG} unexpectedly contains {MARKER!r}")
    ok(f"{ROLLBACK_OLD_TAG} does not contain the rollback marker")

    rollback_new_source = command_output(
        ["docker", "run", "--rm", ROLLBACK_NEW_TAG, "cat", "/app/app.py"],
        timeout=60,
    )
    if MARKER not in rollback_new_source:
        raise RuntimeError(f"{ROLLBACK_NEW_TAG} does not contain {MARKER!r}")
    ok(f"{ROLLBACK_NEW_TAG} contains the rollback marker")


def prepare_step_8() -> None:
    divider("STEP 8: BUILD BOTH IMAGES INSIDE MINIKUBE")
    expected("both minikube image build commands finish without error")

    run(
        [
            "minikube",
            "image",
            "build",
            "-t",
            ROLLBACK_OLD_TAG,
            "-f",
            "weeks/week-11-iac/docker/simple-app.Dockerfile",
            ".",
        ],
        timeout=900,
    )
    ok(f"Built {ROLLBACK_OLD_TAG} inside Minikube")

    run(
        [
            "minikube",
            "image",
            "build",
            "-t",
            ROLLBACK_NEW_TAG,
            "weeks/week-11-iac/manual-image-rollback",
        ],
        timeout=900,
    )
    ok(f"Built {ROLLBACK_NEW_TAG} inside Minikube")


def main() -> None:
    try:
        ensure_prerequisites()
        prepare_step_1()
        prepare_step_2()
        prepare_step_3()
        prepare_step_4()
        prepare_step_5()
        prepare_step_6()
        prepare_step_7()
        prepare_step_8()
    except Exception as exc:
        fail(str(exc))
        sys.exit(1)

    divider("PREPARATION COMPLETE")
    print(
        textwrap.dedent(
            """\
            The image rollback preparation is complete.

            Continue manually from README section 10.2 step 9:
            - cd weeks/week-11-iac/terraform
            - terraform workspace select dev
            - proceed with the manual rollback walkthrough for the professor
            """
        ).rstrip()
    )


if __name__ == "__main__":
    main()
