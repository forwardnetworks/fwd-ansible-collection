"""
Documentation fragment for Forward Networks auth options.
"""


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
options:
  base_url:
    description:
      - Base URL for the Forward Networks instance.
      - Can also be set via C(FORWARD_BASE_URL).
    type: str
  token:
    description:
      - API token for Forward Networks.
      - Can also be set via C(FORWARD_TOKEN).
      - If set, token auth is sent as HTTP Basic with username=<token> and empty password.
    type: str
  username:
    description:
      - Forward username for HTTP Basic auth.
      - Can also be set via C(FWD_USER) or C(FORWARD_USERNAME).
      - Used only when C(token) is not set.
    type: str
  password:
    description:
      - Forward password for HTTP Basic auth.
      - Can also be set via C(FWD_PASS) or C(FORWARD_PASSWORD).
    type: str
  validate_certs:
    description:
      - Whether to validate TLS certificates.
      - Can also be set via C(FORWARD_VALIDATE_CERTS).
    type: bool
    default: true
  timeout:
    description:
      - HTTP timeout (seconds).
      - Can also be set via C(FORWARD_TIMEOUT).
    type: int
    default: 30
"""
