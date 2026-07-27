from flask import Blueprint, Response, request
import logging
import os
import shutil
import time

bp = Blueprint('safe_uploader', __name__)

UPLOAD_FOLDER_ROOT = os.path.join(os.getcwd(), "uploads")

def safe_rmtree(path, retries=5, delay=1):
    for i in range(retries):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError:
            time.sleep(delay)
    try:
        shutil.rmtree(path)
        return True
    except PermissionError as e:
        logging.warning(f"No se pudo borrar {path}: {e}")
        return False


def clean_old_uploads(root_folder, max_age_hours=24):
    now = time.time()
    for folder in os.listdir(root_folder):
        fpath = os.path.join(root_folder, folder)
        if os.path.isdir(fpath):
            age = now - os.path.getmtime(fpath)
            if age > max_age_hours * 3600:
                safe_rmtree(fpath)

@bp.route('/API/resumable', methods=['POST'])
def safe_resumable():
    try:
        upload_id = request.args.get("upload_id")
        identifier = request.args.get("resumableIdentifier")

        if not upload_id or not identifier:
            logging.warning("Faltan parámetros en la solicitud")
            return Response("Missing parameters", status=400)

        temp_dir = os.path.join(UPLOAD_FOLDER_ROOT, upload_id, identifier)

        if not os.path.exists(temp_dir):
            logging.warning(f"Carpeta no encontrada: {temp_dir}")
            return Response("Upload folder not found", status=404)

        safe_rmtree(temp_dir)
        return Response("Upload completed", status=200)

    except Exception as e:
        logging.error(f"Error inesperado en upload: {e}")
        return Response("Upload failed", status=500)



