set -e

# Public English comment.
PORT="${1:-5001}"

# Public English comment.
BACKEND_URI="sqlite:///mlruns.db"
ARTIFACT_ROOT="file://$(pwd)/mlruns"

mkdir -p mlruns

# Public English comment.
mlflow server \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --backend-store-uri "${BACKEND_URI}" \
  --default-artifact-root "${ARTIFACT_ROOT}"
