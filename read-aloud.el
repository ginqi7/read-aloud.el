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

(defvar read-aloud-py-path
  (concat (file-name-directory (or load-file-name (buffer-file-name))) "read-aloud.py")
  "Stores the path to the read-aloud.py file by concatenating the directory of the current file with \"read-aloud.py\".")

;; Custom variables
(defcustom read-aloud-python (executable-find "python3")
  "The Python interpreter."
  :type 'string)

(defcustom read-aloud-notify-command nil
  "Specifies the command for read-aloud notifications, stored as a string."
  :type 'string)

(defcustom read-aloud-transcription-backend "parakeet-mlx"
  "Name of the transcription backend model used by read-aloud. The value should be a string identifying the backend to use (for example, \"parakeet-mlx\", \"deepgram\")."
  :type 'string)

(defcustom read-aloud-deepgram-api-key ""
  "Deepgram API key used for authentication when read-aloud sends audio for transcription. The value should be a string token provided by your Deepgram account."
  :type 'string)

(defcustom read-aloud-aliyun-api-key ""
  "User-configurable API key used to authenticate requests for the read-aloud Paraformer service."
  :type 'string)

(defcustom read-aloud-aliyun-model "paraformer-realtime-v2"
  "Model name for Alibaba Paraformer transcription backend."
  :type 'string)

;; Commands

(defun read-aloud-start ()
  "Start read-aloud."
  (interactive)
  (websocket-bridge-server-start)
  (websocket-bridge-app-start
   "read-aloud"
   read-aloud-python
   read-aloud-py-path))

(defun read-aloud-stop ()
  "Stop read-aloud."
  (interactive)
  (websocket-bridge-app-exit "read-aloud"))

(defun read-aloud-restart ()
  "Restart read-aloud."
  (interactive)
  (read-aloud-stop)
  (read-aloud-start)
  (split-window-below -10)
  (other-window 1)
  (websocket-bridge-app-open-buffer "read-aloud"))

(defun read-aloud-toggle ()
  "Toggles the read-aloud functionality by clearing highlights and sending a \"toggle\" command to \"read-aloud\"."
  (interactive)
  (fuzzy-search--clear-highlights)
  (websocket-bridge-call "read-aloud" "toggle"))

(defun read-aloud-notify (msg)
  "If read-aloud-notify-command is set, displays the message using a shell command; otherwise prints it."
  (if read-aloud-notify-command
      (shell-command-to-string (format read-aloud-notify-command msg))
    (message (format "%s" msg))))

(provide 'read-aloud)
;;; read-aloud.el ends here
