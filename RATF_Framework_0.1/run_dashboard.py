"""PyCharm entry point for the R-ATF dashboard and Flask example."""

from examples.flask_app.app import create_app


if __name__ == "__main__":
    print("Buka http://127.0.0.1:5100/ratf/dashboard/")
    create_app().run(host="127.0.0.1", port=5100, debug=False)
