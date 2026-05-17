# Mock Client

A testing client (`mock_client.py`) that simulates a frontend application interacting with the retrosynthesis backend API.

## Usage

```bash
python mock_client.py <smiles> [options]
```

### Options

- `--backend-url URL` - Backend API URL (default: http://localhost:8000)
- `--min-score SCORE` - Minimum route score to retrieve
- `--timeout SECONDS` - Timeout in seconds (default: 60)

## Examples

Search for caffeine:
```bash
python mock_client.py "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
```

Search for ethanol with minimum score filter:
```bash
python mock_client.py "CCO" --min-score 0.8
```

Use a different backend URL:
```bash
python mock_client.py "CCO" --backend-url http://localhost:8080
```

## Requirements

```bash
pip install -r requirements.txt
```
