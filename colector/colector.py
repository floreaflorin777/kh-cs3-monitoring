"""
Container metrics collector.

Reads per-container stats from the local Docker daemon and POSTs them to
the backend API on a fixed interval. Runs as its own container; the host's
Docker socket is mounted in read-only.
"""
import os
import time
import logging
import requests
import docker

# --- config from environment variables ---
API_URL = os.environ["BACKEND_API_URL"]           # e.g. https://kh-cs3-backend.../measurements
API_KEY = os.environ.get("API_KEY")               # optional, only if your backend requires it
INTERVAL = int(os.environ.get("INTERVAL_SECONDS", "30"))

# --- logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("collector")


def calculate_cpu_percent(stats: dict) -> float:
    """
    Docker reports raw CPU ticks, not a percentage. We compute the delta
    between two consecutive samples to get a usable percent.
    """
    cpu_delta = (
        stats["cpu_stats"]["cpu_usage"]["total_usage"]
        - stats["precpu_stats"]["cpu_usage"]["total_usage"]
    )
    system_delta = (
        stats["cpu_stats"]["system_cpu_usage"]
        - stats["precpu_stats"]["system_cpu_usage"]
    )
    online_cpus = stats["cpu_stats"].get("online_cpus", 1)
    if system_delta > 0 and cpu_delta > 0:
        return round((cpu_delta / system_delta) * online_cpus * 100.0, 2)
    return 0.0


def collect_once(client: docker.DockerClient) -> list[dict]:
    """Snapshot all running containers and return a list of metric dicts."""
    measurements = []
    for container in client.containers.list():
        try:
            stats = container.stats(stream=False)
            cpu_pct = calculate_cpu_percent(stats)
            mem_used = stats["memory_stats"].get("usage", 0)
            mem_limit = stats["memory_stats"].get("limit", 1)
            mem_pct = round((mem_used / mem_limit) * 100.0, 2) if mem_limit else 0.0

            measurements.append({
                "hostname": f"docker:{container.name}",
                "metric": "cpu_percent",
                "value": cpu_pct,
            })
            measurements.append({
                "hostname": f"docker:{container.name}",
                "metric": "memory_percent",
                "value": mem_pct,
            })
        except Exception as exc:
            log.warning("could not read stats for %s: %s", container.name, exc)
    return measurements


def post_measurements(measurements: list[dict]) -> None:
    """Send each measurement to the backend. One bad container should not stop the rest."""
    headers = {"X-API-Key": API_KEY} if API_KEY else {}
    for m in measurements:
        try:
            r = requests.post(API_URL, json=m, headers=headers, timeout=10)
            if not r.ok:
                log.error("post failed for %s: status=%s body=%s",
                          m["hostname"], r.status_code, r.text)
            else:
                log.info("posted %s %s=%s", m["hostname"], m["metric"], m["value"])
        except requests.RequestException as exc:
            log.error("post failed for %s: %s", m["hostname"], exc)


def main() -> None:
    log.info("collector starting, interval=%ds, api=%s", INTERVAL, API_URL)
    client = docker.from_env()  # talks to /var/run/docker.sock
    while True:
        measurements = collect_once(client)
        if measurements:
            post_measurements(measurements)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()