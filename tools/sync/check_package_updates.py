#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License."

import os
import subprocess
from email.mime.text import MIMEText
from smtplib import SMTP


def _send_updates(sender_username, sender_password, receiver_email, updates):
    msg = MIMEText(
        "Here is a list of current Kedro outdated dependencies"
        "\n{}".format("\n".join(updates))
    )
    msg["Subject"] = "Kedro dependencies available updates"
    msg["From"] = sender_username
    msg["To"] = receiver_email
    s = SMTP(host="smtp.office365.com", port=587)
    s.starttls()
    s.login(user=sender_username, password=sender_password)
    s.send_message(msg)
    s.quit()


def _get_updates():
    result = subprocess.run(["pip", "list", "--outdated"], stdout=subprocess.PIPE)
    updated_packages = result.stdout.decode("utf-8").split("\n")
    return updated_packages


if __name__ == "__main__":
    sender_username = os.environ["KEDRO_NOTIFICATIONS_USER"]
    sender_password = os.environ["KEDRO_NOTIFICATIONS_PASSWORD"]
    receiver_email = os.environ["KEDRO_DISTRIBUTION"]
    package_updates = _get_updates()

    if package_updates:
        _send_updates(sender_username, sender_password, receiver_email, package_updates)
