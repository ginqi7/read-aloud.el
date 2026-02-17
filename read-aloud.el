;;; read-aloud.el ---                               -*- lexical-binding: t; -*-

;; Copyright (C) 2025  Qiqi Jin

;; Author: Qiqi Jin <ginqi7@gmail.com>
;; Keywords:

;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation, either version 3 of the License, or
;; (at your option) any later version.

;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with this program.  If not, see <https://www.gnu.org/licenses/>.

;;; Commentary:

;;

;;; Code:
(require 'websocket-bridge)
(require 'fuzzy-search)

(defvar read-alound-py-path
  (concat (file-name-directory (or load-file-name (buffer-file-name))) "read-alound.py")
  "Stores the path to the read-alound.py file by concatenating the directory of the current file with \"read-alound.py\".")

;; Custom variables
(defcustom read-alound-python (executable-find "python3")
  "The Python interpreter."
  :type 'string)

(defcustom read-alound-notify-command nil
  "Specifies the command for read-alound notifications, stored as a string."
  :type 'string)

(defcustom read-alound-transcription-backend "parakeet-mlx"
  "Name of the transcription backend model used by read-alound. The value should be a string identifying the backend to use (for example, \"parakeet-mlx\", \"deepgram\")."
  :type 'string)

(defcustom read-alound-deepgram-api-key ""
  "Deepgram API key used for authentication when read-alound sends audio for transcription. The value should be a string token provided by your Deepgram account."
  :type 'string)

(defcustom read-alound-paraformer-api-key ""
  "User-configurable API key used to authenticate requests for the read-aloud Paraformer service."
  :type 'string)

;; Commands

(defun read-alound-start ()
  "Start read-alound."
  (interactive)
  (websocket-bridge-server-start)
  (websocket-bridge-app-start
   "read-alound"
   read-alound-python
   read-alound-py-path))

(defun read-alound-stop ()
  "Stop read-alound."
  (interactive)
  (websocket-bridge-app-exit "read-alound"))

(defun read-alound-restart ()
  "Restart read-alound."
  (interactive)
  (read-alound-stop)
  (read-alound-start)
  (split-window-below -10)
  (other-window 1)
  (websocket-bridge-app-open-buffer "read-alound"))

(defun read-alound-toggle ()
  "Toggles the read-alound functionality by clearing highlights and sending a \"toggle\" command to \"read-alound\"."
  (interactive)
  (fuzzy-search--clear-highlights)
  (websocket-bridge-call "read-alound" "toggle"))

(defun read-alound-notify (msg)
  "If read-alound-notify-command is set, displays the message using a shell command; otherwise prints it."
  (if read-alound-notify-command
      (shell-command-to-string (format read-alound-notify-command msg))
    (message (format "%s" msg))))

(provide 'read-aloud)
;;; read-aloud.el ends here
