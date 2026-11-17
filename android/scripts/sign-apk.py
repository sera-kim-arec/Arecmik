"""Sign the personal APK; private signing material stays outside the repository."""
import hashlib
import json
import re
import shutil
import os
from pathlib import Path
import secrets
import subprocess

repo = Path(__file__).resolve().parents[2]
sdk = Path(os.environ['ANDROID_HOME'])
tools = sdk / 'build-tools/35.0.0'
signing = Path(os.environ.get('ARECMIK_SIGNING_DIR', str(repo.parent / 'arecmik-signing')))
signing.mkdir(mode=0o700, parents=True, exist_ok=True)
password = signing / 'password'
keystore = signing / 'widget.jks'
if not password.exists():
    password.write_text(secrets.token_urlsafe(36))
    password.chmod(0o600)
if not keystore.exists():
    subprocess.run([str(Path(os.environ['JAVA_HOME'])/'bin/keytool'), '-genkeypair',
                    '-keystore', str(keystore), '-alias', 'arecmik', '-keyalg', 'RSA',
                    '-keysize', '3072', '-validity', '10000', '-dname', 'CN=Arecmik Personal Widget',
                    '-storepass:file', str(password), '-keypass:file', str(password)], check=True)
    keystore.chmod(0o600)
source = repo / 'android/app/build/outputs/apk/release/app-release-unsigned.apk'
aligned = source.parent / 'app-release-aligned.apk'
gradle = (repo / 'android/app/build.gradle').read_text()
version_name = re.search(r"versionName '([0-9.]+)'", gradle).group(1)
version_code = int(re.search(r'versionCode (\d+)', gradle).group(1))
output = repo / ('downloads/Arecmik-'+version_name+'.apk')
output.parent.mkdir(exist_ok=True)
subprocess.run([str(tools/'zipalign'), '-f', '-p', '4', str(source), str(aligned)], check=True)
subprocess.run([str(tools/'apksigner'), 'sign', '--ks', str(keystore), '--ks-key-alias', 'arecmik',
                '--ks-pass', 'file:'+str(password), '--v4-signing-enabled', 'false',
                '--out', str(output), str(aligned)], check=True)
subprocess.run([str(tools/'apksigner'), 'verify', '--verbose', '--print-certs', str(output)], check=True)
digest = hashlib.sha256(output.read_bytes()).hexdigest()
shutil.copyfile(output, output.with_name('Arecmik-latest.apk'))
output.with_name('SHA256SUMS.txt').write_text(digest+'  '+output.name+'\n'+digest+'  Arecmik-latest.apk\n')
(repo / 'android-release.json').write_text(json.dumps({'versionCode':version_code,'versionName':version_name,'url':'https://sera-kim-arec.github.io/Arecmik/downloads/'+output.name,'sha256':digest},indent=2)+'\n')
print('Signed installation APK:', output)
