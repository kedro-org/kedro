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
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.


def matcher(r1, r2):  # pylint: disable=too-many-return-statements
    if r2.uri != r1.uri:
        return False
    if r1.method != r2.method:
        return False
    if r1.method != "POST" and r1.body != r2.body:
        return False
    if r1.method == "POST":
        try:
            r1_body, r2_body = r1.body.decode(), r2.body.decode()
            r1_body = r1_body.replace("--===============[0-9]+==\r\ncontent-type", "")
            r2_body = r1_body.replace("--===============[0-9]+==\r\ncontent-type", "")

            return r1_body == r2_body
        except:  # NOQA   # pylint: disable=bare-except
            pass
        r1q = (r1.body or b"").split(b"&")
        r2q = (r2.body or b"").split(b"&")
        for q in r1q:
            if b"secret" in q or b"token" in q:
                continue
            if q not in r2q:
                return False
    else:
        for key in ["Content-Length", "Content-Type", "Range"]:
            if key in r1.headers and key in r2.headers:
                if r1.headers.get(key, "") != r2.headers.get(key, ""):
                    return False
    return True
