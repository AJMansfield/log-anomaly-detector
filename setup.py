""" Setup.py for packaging log-anomaly-detector as library """
from setuptools import setup, find_packages

long_description = "Log Anomaly Detection - Machine learning to detect abnormal events logs"


REQUIRED_PKG = [
    "Click",
    "elasticsearch5",
    "gensim==3.8.1",
    "matplotlib",
    "Cython==0.29.24",
    "tensorflow==2.7.0",
    "numpy<1.23.0",
    "pandas==1.3.3",
    "prometheus_client",
    "Flask==1.0.4",
    "scikit-learn==1.0.1",
    "scipy==1.7.1",
    "tqdm",
    "SQLAlchemy<2.0",
    "PyMySQL",
    "scikit-image<0.20.0",
    "sompy @ git+https://github.com/sevamoo/SOMPY.git",
    "boto3",
    "pyyaml==5.3.1",
    "numba",
    "kafka-python",
    "jaeger-client",
    "opentracing_instrumentation",
    "prometheus_flask_exporter",
    "gunicorn==19.9.0",
    "flask_sqlalchemy<3.0",
    "tornado==5.1.1",
    "pymongo==3.12.1",
    "mysql-connector-python==8.0.27",
    "protobuf<=3.20",
    "urllib3<1.27,>=1.25.4",
    "Jinja2<3.1",
    "itsdangerous<2.1",
]

setup(
    name="log-anomaly-detector",
    version="0.6.0",
    py_modules=['lad'],
    packages=find_packages(),
    setup_requires=["pytest-runner"],
    tests_require=[
        "pytest",
        "pytest-sugar",
        "pytest-xdist"],
    zip_safe=False,
    classifiers=(
        "Development Status :: 1 - Planning",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.8",
    ),
    python_requires=">3.5",
    url="https://github.com/AJMansfield//log-anomaly-detector",
    author="Anson Mansfield",
    author_email="amansfield@mantaro.com",
    description="Log anomaly detector for streaming logs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    dependency_links=[
	"git+https://github.com/sevamoo/SOMPY.git",
    ],
    install_requires=REQUIRED_PKG,
    entry_points="""
        [console_scripts]
        log-anomaly-detector=lad:cli
    """,
)
