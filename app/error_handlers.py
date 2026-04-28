from flask import Flask, flash, redirect, render_template, url_for


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def payload_too_large(_error):
        flash(
            "Upload too large. Each request is limited to 16 MB. "
            "Please upload smaller batches or compress the images.",
            "warning",
        )
        return redirect(url_for("main.history"))

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500
