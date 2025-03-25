from flask import Flask, request, render_template, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import json
import yaml
import requests
from urllib.parse import urlparse
import time
from datetime import datetime
from sqlalchemy import JSON
import psycopg2

app = Flask(__name__)
# PostgreSQL Configuration
DB_USER = "postgres"
DB_PASSWORD = "0816"
DB_HOST = "localhost"
DB_PORT = "5432"
DB_NAME = "api_scanner"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Update models to use JSONB
class ApiDocumentation(db.Model):
    __tablename__ = "api_documentation"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    host = db.Column(db.String(200))
    spec_type = db.Column(db.String(50))
    spec_version = db.Column(db.String(20))
    base_path = db.Column(db.String(200))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text)

    endpoints = db.relationship("ApiEndpoint", backref="documentation", lazy=True)


class ApiEndpoint(db.Model):
    __tablename__ = "api_endpoint"

    id = db.Column(db.Integer, primary_key=True)
    documentation_id = db.Column(db.Integer, db.ForeignKey("api_documentation.id"))
    scheme = db.Column(db.String(10))
    method = db.Column(db.String(10))
    server = db.Column(db.String(200))
    base_path = db.Column(db.String(200))
    path = db.Column(db.String(500))
    status_codes = db.Column(db.String(200))
    description = db.Column(db.Text)
    path_params = db.Column(db.JSON)  # Using JSON type for parameters
    query_params = db.Column(db.JSON)
    body_params = db.Column(db.JSON)


# After updating the models, you need to recreate the database
def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database tables created successfully")


@app.route("/", methods=["GET"])
def upload_page():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload():
    try:
        # Debug incoming request
        print("=== Upload Request Debug ===")
        print(f"Files: {request.files}")
        print(f"Form data: {request.form}")

        file = request.files.get("spec_file")
        host = request.form.get("host", "").strip()
        name = request.form.get("name", "").strip()

        if not file or not host:
            error_msg = "File and host are required."
            print(f"Validation error: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        # Debug file info
        print(f"File name: {file.filename}")
        print(f"File content type: {file.content_type}")

        # Read file content
        try:
            content = file.read().decode("utf-8")
            print(f"Content length: {len(content)}")
            print(f"Content preview: {content[:200]}")  # First 200 chars

            # Parse content based on file type
            if file.filename.endswith(".json"):
                spec = json.loads(content)
            elif file.filename.endswith((".yaml", ".yml")):
                spec = yaml.safe_load(content)
            else:
                error_msg = "Unsupported file format"
                print(f"Format error: {error_msg}")
                return jsonify({"success": False, "error": error_msg}), 400

            print(f"Parsed spec type: {type(spec)}")
            print(
                f"Spec keys: {spec.keys() if isinstance(spec, dict) else 'Not a dict'}"
            )

        except Exception as e:
            error_msg = f"Error parsing file: {str(e)}"
            print(f"Parse error: {error_msg}")
            print(f"Content causing error: {content}")
            return jsonify({"success": False, "error": error_msg}), 400

        # Process host URL
        try:
            if not host.startswith(("http://", "https://")):
                host = f"https://{host}"

            parsed_url = urlparse(host)
            server = parsed_url.netloc
            base_path = parsed_url.path.rstrip("/")
            scheme = parsed_url.scheme or "https"

            print(
                f"Processed URL - Server: {server}, Base Path: {base_path}, Scheme: {scheme}"
            )

        except Exception as e:
            error_msg = f"Error processing host URL: {str(e)}"
            print(f"URL error: {error_msg}")
            return jsonify({"success": False, "error": error_msg}), 400

        # Create documentation entry
        try:
            api_doc = ApiDocumentation(
                name=name or server,
                host=host,
                base_path=base_path,
                spec_type="OpenAPI",
                spec_version=spec.get("openapi", spec.get("swagger", "unknown")),
                description=spec.get("info", {}).get("description"),
                uploaded_at=datetime.utcnow(),
            )
            db.session.add(api_doc)
            db.session.flush()
            print(f"Created documentation entry: ID={api_doc.id}")

        except Exception as e:
            error_msg = f"Error creating documentation entry: {str(e)}"
            print(f"DB error: {error_msg}")
            db.session.rollback()
            return jsonify({"success": False, "error": error_msg}), 400

        # Process endpoints
        try:
            paths = spec.get("paths", {})
            print(f"Processing {len(paths)} paths")

            for path, path_data in paths.items():
                for method, details in path_data.items():
                    if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                        continue

                    print(f"Processing endpoint: {method.upper()} {path}")

                    # Process parameters
                    parameters = details.get("parameters", []) + path_data.get(
                        "parameters", []
                    )
                    path_params = []
                    query_params = []

                    for param in parameters:
                        param_info = {
                            "name": param.get("name", ""),
                            "type": param.get("schema", {}).get(
                                "type", param.get("type", "string")
                            ),
                            "required": param.get("required", False),
                            "description": param.get("description", ""),
                        }

                        if param.get("in") == "path":
                            path_params.append(param_info)
                        elif param.get("in") == "query":
                            query_params.append(param_info)

                    # Create endpoint
                    endpoint = ApiEndpoint(
                        documentation_id=api_doc.id,
                        scheme=scheme,
                        method=method.upper(),
                        server=server,
                        base_path=base_path,
                        path=path,
                        description=details.get("description", ""),
                        path_params=path_params,
                        query_params=query_params,
                        body_params=details.get("requestBody", {})
                        .get("content", {})
                        .get("application/json", {})
                        .get("schema", {}),
                        status_codes=",".join(details.get("responses", {}).keys()),
                    )
                    db.session.add(endpoint)

            db.session.commit()
            print("Successfully committed all changes")

            return jsonify(
                {
                    "success": True,
                    "doc_id": api_doc.id,
                    "message": f"Successfully uploaded {name or server} with {len(paths)} paths",
                }
            )

        except Exception as e:
            error_msg = f"Error processing endpoints: {str(e)}"
            print(f"Processing error: {error_msg}")
            db.session.rollback()
            return jsonify({"success": False, "error": error_msg}), 400

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(f"Global error: {error_msg}")
        return jsonify({"success": False, "error": error_msg}), 500


@app.route("/endpoints")
def view_endpoints():
    endpoints = ApiEndpoint.query.all()
    return render_template("endpoint.html", endpoints=endpoints)


@app.route("/test_endpoint", methods=["POST"])
def test_endpoint():
    try:
        data = request.json
        endpoint_id = data.get("endpoint_id")
        endpoint = ApiEndpoint.query.get_or_404(endpoint_id)

        # Ensure path_params is a dictionary
        path_params = data.get("path_params", {})
        if isinstance(path_params, list):
            # Convert list to dict if needed
            path_params = {
                param.get("name"): param.get("value")
                for param in path_params
                if param.get("name")
            }

        # Construct proper URL
        if ":" in endpoint.server:  # If port is included in server
            server_parts = endpoint.server.split(":")
            host = server_parts[0]
            port = server_parts[1]
            base_url = f"{endpoint.scheme}://{host}:{port}"
        else:
            base_url = f"{endpoint.scheme}://{endpoint.server}"

        # Build full URL
        url = base_url.rstrip("/") + "/" + endpoint.path.lstrip("/")

        print(f"Testing URL: {url}")  # Debug log

        # Replace path parameters
        for param_name, param_value in path_params.items():
            url = url.replace(f"{{{param_name}}}", str(param_value))

        print(f"Final URL with parameters: {url}")  # Debug log

        # Make the request
        response = requests.request(
            method=endpoint.method,
            url=url,
            headers=data.get("headers", {}),
            json=data.get("body"),
            verify=False,  # For self-signed certificates
            timeout=10,  # Add timeout
        )

        return jsonify(
            {
                "status": response.status_code,
                "headers": dict(response.headers),
                "body": response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else response.text,
            }
        )

    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return jsonify({"error": f"Request failed: {str(e)}"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()  # Print full traceback
        return jsonify({"error": str(e)}), 500


@app.route("/massive_test")
def massive_test():
    try:
        # Get the selected doc_id from query params, default to None
        selected_doc_id = request.args.get("doc_id", type=int)

        # Get all API documentations and add debug logging
        documentations = ApiDocumentation.query.all()
        print(f"Found {len(documentations)} documentations:")
        for doc in documentations:
            print(f"- ID: {doc.id}, Name: {doc.name}, Host: {doc.host}")

        # If no doc_id selected and we have documentations, select the first one
        if not selected_doc_id and documentations:
            selected_doc_id = documentations[0].id
            print(f"Selected first documentation with ID: {selected_doc_id}")
        else:
            print(f"Using selected doc_id: {selected_doc_id}")

        # Get endpoints for selected documentation
        grouped_endpoints = {}
        if selected_doc_id:
            endpoints = ApiEndpoint.query.filter_by(
                documentation_id=selected_doc_id
            ).all()
            print(f"Found {len(endpoints)} endpoints for doc_id {selected_doc_id}")

            # Group endpoints by their path prefix
            for endpoint in endpoints:
                path_parts = endpoint.path.strip("/").split("/")
                group = path_parts[0] if path_parts else "default"

                if group not in grouped_endpoints:
                    grouped_endpoints[group] = []
                grouped_endpoints[group].append(endpoint)

            print(f"Grouped endpoints into {len(grouped_endpoints)} groups")

        print("Rendering template with:")
        print(f"- {len(documentations)} documentations")
        print(f"- Selected doc_id: {selected_doc_id}")
        print(f"- {len(grouped_endpoints)} endpoint groups")

        return render_template(
            "massive_test.html",
            documentations=documentations,
            selected_doc_id=selected_doc_id,
            grouped_endpoints=grouped_endpoints,
        )

    except Exception as e:
        print(f"Error in massive_test route: {str(e)}")
        import traceback

        traceback.print_exc()
        return str(e), 500


def init_db():
    with app.app_context():
        print("Starting database initialization...")
        # Drop all tables
        db.drop_all()
        print("Dropped all tables")

        # Create all tables
        db.create_all()
        print("Created all tables")

        # Verify tables were created
        from sqlalchemy import inspect

        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {tables}")

        print("Database initialization complete")


@app.route("/api/analyze_endpoints")
@app.route("/api/analyze_endpoints/<int:doc_id>")
def analyze_endpoints(doc_id=None):
    try:
        # Get endpoints filtered by doc_id if provided
        if doc_id:
            endpoints = ApiEndpoint.query.filter_by(documentation_id=doc_id).all()
            print(f"Found {len(endpoints)} endpoints for documentation {doc_id}")

            # Get specific documentation
            doc = ApiDocumentation.query.get(doc_id)
            if not doc:
                return jsonify({"error": f"Documentation {doc_id} not found"}), 404

            doc_map = {doc.id: doc}
        else:
            # Get all endpoints (fallback behavior)
            endpoints = ApiEndpoint.query.all()
            print(f"Found {len(endpoints)} total endpoints")

            # Get all docs
            docs = ApiDocumentation.query.all()
            print(f"Found {len(docs)} API documentations")
            doc_map = {doc.id: doc for doc in docs}

        result = {
            "endpoints": [
                {
                    "documentation_id": endpoint.documentation_id,
                    "method": endpoint.method,
                    "scheme": endpoint.scheme,
                    "server": endpoint.server,
                    "path": endpoint.path,
                    "path_params": endpoint.path_params,
                    "query_params": endpoint.query_params,
                    "base_path": doc_map[endpoint.documentation_id].base_path
                    if endpoint.documentation_id in doc_map
                    else None,
                    "original_host": doc_map[endpoint.documentation_id].host
                    if endpoint.documentation_id in doc_map
                    else None,
                }
                for endpoint in endpoints
            ]
        }

        print(f"Returning {len(result['endpoints'])} endpoints")
        return jsonify(result)
    except Exception as e:
        print(f"Error analyzing endpoints: {e}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/run_massive_test", methods=["POST"])
def run_massive_test():
    try:
        data = request.json
        test_config = data.get("testConfig", {})
        results = []

        for endpoint in data.get("endpoints", []):
            try:
                print("\n=== Debug URL Construction ===")
                print(f"Original endpoint data: {endpoint}")

                # Get the documentation to access the base_path
                doc = ApiDocumentation.query.get(endpoint.get("documentation_id"))
                if doc:
                    parsed_url = urlparse(doc.host)
                    base_path = parsed_url.path
                else:
                    base_path = "/api/v1"  # fallback default

                # Construct proper URL with scheme and base path
                scheme = endpoint.get("scheme", "https")
                server = endpoint["server"]
                test_path = endpoint["path"]

                # Build full URL properly
                url = f"{scheme}://{server}"

                # Add base path if present (ensure no double slashes)
                if base_path:
                    url += ("/" + base_path.strip("/")) if base_path.strip("/") else ""

                # Add endpoint path (ensure no double slashes)
                url += ("/" + test_path.strip("/")) if test_path else ""

                print(f"URL Components:")
                print(f"- Scheme: {scheme}")
                print(f"- Server: {server}")
                print(f"- Base Path: {base_path}")
                print(f"- Test Path: {test_path}")
                print(f"- Final URL: {url}")

                # Handle path parameters
                if isinstance(endpoint.get("path_params"), str):
                    path_params = json.loads(endpoint.get("path_params", "[]"))
                else:
                    path_params = endpoint.get("path_params", [])

                # Replace path parameters
                for param in path_params:
                    param_name = param.get("name")
                    param_value = test_config.get(param_name, f"test_{param_name}")
                    url = url.replace(f"{{{param_name}}}", str(param_value))

                print(f"Final URL with parameters: {url}")

                # Make the request
                start_time = time.time()
                response = requests.request(
                    method=endpoint["method"],
                    url=url,
                    headers=test_config.get("headers", {}),
                    json=test_config.get("body", {}),
                    verify=False,
                    timeout=10,
                )
                response_time = round((time.time() - start_time) * 1000)

                results.append(
                    {
                        "endpoint": f"{endpoint['method']} {endpoint['path']}",
                        "test_url": url,
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "success": response.status_code < 400,
                        "needs_attention": response.status_code
                        not in [200, 201, 204, 401, 403],
                        "response": response.text[:200],
                        "error": None,
                    }
                )

            except Exception as e:
                print(f"Error testing endpoint: {str(e)}")
                results.append(
                    {
                        "endpoint": f"{endpoint['method']} {endpoint['path']}",
                        "test_url": url
                        if "url" in locals()
                        else "URL construction failed",
                        "status_code": None,
                        "response_time": None,
                        "success": False,
                        "needs_attention": True,
                        "response": None,
                        "error": str(e),
                    }
                )

        return jsonify(
            {
                "total_endpoints": len(results),
                "successful_tests": sum(1 for r in results if r["success"]),
                "failed_tests": sum(1 for r in results if not r["success"]),
                "needs_attention": sum(1 for r in results if r["needs_attention"]),
                "results": results,
            }
        )

    except Exception as e:
        print(f"Error in massive_test: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/test_endpoint/<int:endpoint_id>", methods=["POST"])
def test_endpoint1(endpoint_id):
    try:
        endpoint = ApiEndpoint.query.get_or_404(endpoint_id)
        params = request.json

        # Build the URL with parameters
        url = f"{endpoint.server}{endpoint.path}"

        # Replace path parameters
        for param_name, param_value in params.get("path", {}).items():
            url = url.replace(f"{{{param_name}}}", param_value)

        # Add query parameters
        if params.get("query"):
            url += "?" + "&".join(f"{k}={v}" for k, v in params["query"].items())

        # Make the request
        response = requests.request(
            method=endpoint.method,
            url=url,
            json=params.get("body"),
            headers=params.get("headers", {}),
        )

        return jsonify(
            {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json()
                if response.headers.get("content-type", "").startswith(
                    "application/json"
                )
                else response.text,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/save_parameters", methods=["POST"])
def save_parameters():
    try:
        parameters = request.json

        # Update the database with the new parameters
        for endpoint in ApiEndpoint.query.all():
            # Find matching parameters for this endpoint
            path_params = [
                p
                for p in parameters["path"]
                if p["endpoint"] == f"{endpoint.method} {endpoint.path}"
            ]
            query_params = [
                p
                for p in parameters["query"]
                if p["endpoint"] == f"{endpoint.method} {endpoint.path}"
            ]

            # Update the endpoint's parameters
            endpoint.path_params = json.dumps(path_params)
            endpoint.query_params = json.dumps(query_params)

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    init_db()  # Initialize the database
    app.run(debug=True)
