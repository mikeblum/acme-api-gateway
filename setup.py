from distutils.core import setup

setup(
    name='lets-encrypt-api-gateway',
    version='0.1dev',
    description='Generate Certificates for AWS API Gateway',
    author='Michael Blum',
    author_email='me@mblum.me',
    url='https://www.github.com/mikeblum/lets-encrypt-api-gateway',
    packages=['letsencrypt-api-gateway'],
    license='MIT',
    long_description=open('README.md').read(),
)