import logging
import os
import subprocess
import time

import requests

DNS_ZONE_ID = os.environ["DNS_ZONE_ID"]  # in www
CERTIFIATE_FOLDER_ID = os.environ["CERTIFIATE_FOLDER_ID"]  # id of k8s-demo folder


def get_token():
    url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    r = requests.get(url, headers={"Metadata-Flavor": "Google"})
    response = r.json()
    return response["access_token"]


def get_certs_from_file():
    with open("/.acme.sh/*.demo.ytsaurus.tech/fullchain.cer", "r") as f:
        chain = f.read()
    with open("/.acme.sh/*.demo.ytsaurus.tech/*.demo.ytsaurus.tech.key", "r") as f:
        key = f.read()
    with open("/.acme.sh/*.demo.ytsaurus.tech/*.demo.ytsaurus.tech.cer", "r") as f:
        cert = f.read()
    return cert, key, chain


def run_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, _ = process.communicate()
    return stdout.decode("utf-8")


def initialize_account():
    cmd = "acme.sh --register-account -m kozubaeff@yandex-team.ru"
    res = run_command(cmd)
    logging.info(res)
    logging.info("Created account for acme.sh")


def issue_cert():
    issue_cmd = "acme.sh --issue -d *.demo.ytsaurus.tech --dns --keylength 2048  --yes-I-know-dns-manual-mode-enough-go-ahead-please"
    res = run_command(issue_cmd).split("\n")
    logging.info("Got from inner command: {}".format(res))
    if "Domain" not in res[6].split("'")[0]:
        raise RuntimeError("Unable to parse certs")
    domain = res[6].split("'")[1]
    if "TXT value" not in res[7].split("'")[0]:
        raise RuntimeError("Unable to parse certs")
    txt_value = res[7].split("'")[1]
    logging.info("Certificate issued for domain {}".format(domain))
    return domain.strip(), txt_value.strip()


def create_dns_record(token, domain, txt_value):
    domain += "."
    url = "https://dns.api.cloud.yandex.net/dns/v1/zones/{}:upsertRecordSets".format(DNS_ZONE_ID)
    headers = {"Authorization": "Bearer {}".format(token)}
    data = {
        "deletions": [],
        "replacements": [],
        "merges": [{"name": domain, "type": "TXT", "ttl": 300, "data": [txt_value]}],
    }
    r = requests.post(url, headers=headers, json=data)
    r.raise_for_status()
    logging.info("DNS record created")


def renew_cert():
    renew_cmd = "acme.sh --renew -d *.demo.ytsaurus.tech \
          --dns --keylength 2048 --yes-I-know-dns-manual-mode-enough-go-ahead-please"
    output = run_command(renew_cmd)
    logging.info(output)
    if "Cert success" not in output:
        raise Exception("Certificate renewal failed")
    else:
        logging.info("Certificate renewed")


def update_old_certs(token):
    url = "https://certificate-manager.api.cloud.yandex.net/certificate-manager/v1/certificates?folderId={}".format(CERTIFIATE_FOLDER_ID)
    headers = {"Authorization": "Bearer {}".format(token)}
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    old_cert = next(filter(lambda x: "*.demo.ytsaurus.tech" in x["domains"], r.json()["certificates"]))

    cert, key, chain = get_certs_from_file()
    url = "https://certificate-manager.api.cloud.yandex.net/certificate-manager/v1/certificates/{}".format(old_cert["id"])
    data = {
        "privateKey": key,
        "chain": chain,
        "certificate": cert,
    }
    r = requests.patch(url, headers=headers, json=data)
    logging.warning(r.json())
    r.raise_for_status()
    logging.info("Old certificates updated")


def main():
    token = get_token()
    initialize_account()
    domain, txt_value = issue_cert()
    create_dns_record(token, domain, txt_value)
    logging.info("Sleeping for 120 seconds")
    time.sleep(120)
    renew_cert()
    update_old_certs(token)


if __name__ == "__main__":
    main()
