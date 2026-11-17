"""Reproduce the Linux cloud toolchain without modifying system directories."""
from pathlib import Path
import hashlib
import os
import shlex
import subprocess
import tarfile
import urllib.parse
import zipfile

base = Path(os.environ.get('ARECMIK_ANDROID_TOOLS', '/workspace/android-tools'))
base.mkdir(parents=True, exist_ok=True)


def artifact(name, url, digest, algorithm='sha256'):
    path = base / name
    if not path.exists() or hashlib.new(algorithm, path.read_bytes()).hexdigest() != digest:
        temp = path.with_suffix(path.suffix+'.part')
        subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--max-time', '300', url, '-o', str(temp)], check=True)
        if hashlib.new(algorithm, temp.read_bytes()).hexdigest() != digest:
            raise RuntimeError(name+' checksum did not match; the artifact was not used')
        temp.replace(path)
    return path


def unzip(path, destination):
    with zipfile.ZipFile(path) as archive:
        archive.extractall(destination)
        for item in archive.infolist():
            if item.external_attr >> 16:
                os.chmod(destination/item.filename, (item.external_attr >> 16) & 0o777)


jdk = base/'jdk/jdk-17.0.20.1+1'
jdk_archive = artifact('jdk.tar.gz', 'https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jdk_x64_linux_hotspot_17.0.20.1_1.tar.gz', '3808d1d15e3ec6bd5b84057fb5d84c33d8a1536a258146bcea2e603fc726e08e')
if not (jdk/'bin/javac').exists():
    with tarfile.open(jdk_archive) as archive:
        archive.extractall(base/'jdk', filter='data')
gradle_archive = artifact('gradle.zip', 'https://downloads.gradle.org/distributions/gradle-8.13-bin.zip', '20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78')
if not (base/'gradle-8.13/bin/gradle').exists():
    unzip(gradle_archive, base)
cmdline = artifact('cmdline.zip', 'https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip', '2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258')
sdk = base/'sdk'
if not (sdk/'cmdline-tools/bootstrap/cmdline-tools/bin/sdkmanager').exists():
    unzip(cmdline, sdk/'cmdline-tools/bootstrap')
artifact('android-all-instrumented-15-robolectric-12650502-i7.jar', 'https://repo.maven.apache.org/maven2/org/robolectric/android-all-instrumented/15-robolectric-12650502-i7/android-all-instrumented-15-robolectric-12650502-i7.jar', '87bdd0341838f5f630e1ff412ab29cb2f06e0f8cb7751f14679d11b4ee6084873001f8f6a8581ae6e139fa7c9a654b632412827430f984ebecc3c2588674f7e7', 'sha512')
env = os.environ.copy()
settings = {'JAVA_HOME': str(jdk), 'ANDROID_HOME': str(sdk), 'ANDROID_USER_HOME': str(base/'android-user'), 'GRADLE_USER_HOME': str(base/'gradle-home')}
for key in ['ANDROID_USER_HOME', 'GRADLE_USER_HOME']:
    Path(settings[key]).mkdir(exist_ok=True)
trust = Path('/etc/ssl/certs/java/cacerts')
if trust.exists():
    settings['JAVA_TOOL_OPTIONS'] = '-Djavax.net.ssl.trustStore='+str(trust)
env.update(settings)
proxy = urllib.parse.urlparse(env.get('HTTPS_PROXY') or env.get('https_proxy') or '')
proxy_args = []
if proxy.hostname:
    proxy_args = ['--proxy=http', '--proxy_host='+proxy.hostname, '--proxy_port='+str(proxy.port or 80)]
    properties = ''.join('systemProp.'+scheme+'.proxyHost='+proxy.hostname+'\nsystemProp.'+scheme+'.proxyPort='+str(proxy.port or 80)+'\n' for scheme in ['http','https'])
    (base/'gradle-home/gradle.properties').write_text(properties)
if not all(path.exists() for path in [sdk/'platforms/android-35/android.jar', sdk/'build-tools/35.0.0/apksigner', sdk/'platform-tools/adb']):
    subprocess.run([str(sdk/'cmdline-tools/bootstrap/cmdline-tools/bin/sdkmanager'), '--sdk_root='+str(sdk), *proxy_args, 'platforms;android-35', 'build-tools;35.0.0', 'platform-tools'], input='y\n'*32, text=True, env=env, check=True)
(base/'environment.sh').write_text('\n'.join('export '+name+'='+shlex.quote(value) for name,value in settings.items())+'\n')
subprocess.run([str(jdk/'bin/javac'), '-version'], env=env, check=True)
print('Android toolchain verified; source', base/'environment.sh', 'before building.')
