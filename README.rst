🎵 OpenLP NCSDA (Noir + EGW Library)
====================================

|pipeline| |license| |python| |qt| |platform| |edition|

.. |pipeline| image:: https://gitlab.com/JosiahAgency/openlp/badges/NCSDA_Version/pipeline.svg
   :target: https://gitlab.com/JosiahAgency/openlp/-/pipelines
   :alt: Pipeline status

.. |license| image:: https://img.shields.io/badge/license-GPL--3.0-2ea44f.svg
   :target: https://www.gnu.org/licenses/gpl-3.0.html
   :alt: License: GPL-3.0

.. |python| image:: https://img.shields.io/badge/python-3.10%2B-3776AB.svg?logo=python&logoColor=white
   :target: https://www.python.org/
   :alt: Python 3.10+

.. |qt| image:: https://img.shields.io/badge/Qt-PySide6-41CD52.svg?logo=qt&logoColor=white
   :target: https://doc.qt.io/qtforpython-6/
   :alt: Qt for Python (PySide6)

.. |platform| image:: https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-6f42c1.svg
   :alt: Windows, Linux and macOS

.. |edition| image:: https://img.shields.io/badge/edition-NCSDA%20Noir-16161d.svg
   :alt: NCSDA Noir edition

This repository is a customized OpenLP edition focused on church presentation
workflows for Ellen G. White content and a redesigned modern interface.

It is based on upstream OpenLP, with two major additions:

1. 📚 **EGW Library plugin** for importing, searching, and presenting Ellen G.
   White books at paragraph-level citation granularity.
2. 🌒 **Noir UI theme** for a cleaner, darker, modern presentation and operator
   experience.

⚠️ This is **not** the standard OpenLP release.

✨ Highlights
-------------

📚 EGW Library plugin
~~~~~~~~~~~~~~~~~~~~~

* 📥 Import books from JSON files (single book or multi-book files).
* 📄 Optional direct conversion from EGW Estate PDF exports into plugin JSON.
* 🔍 Smart reference parsing (examples: ``DA 83.2``, ``DA 83-85``, ``DA ch 5``).
* ⚡ Full-text paragraph search with database indexing and fallback behavior.
* 🖥️ Service item generation with EGW-aware references and optional footer output.
* 🎛️ Configurable EGW display theme and footer reference visibility.

🌒 Noir UI theme
~~~~~~~~~~~~~~~~

* 🌑 New dark, modern visual language across key UI areas.
* 🎬 Slide and service list presentation refinements for live operation.
* 🎨 Themed icon set and palette updates tailored for high-contrast readability.
* 💿 Dedicated installer branding as **OpenLP Noir**.

🏷️ Project identity
--------------------

This edition is maintained as the **NCSDA Version** and includes custom
features that are not part of upstream OpenLP.

If you need stock OpenLP, visit:

* https://openlp.org/

🚀 Quick start (source)
-----------------------

📋 Requirements
~~~~~~~~~~~~~~~

* 🐍 Python 3.10+
* 🧩 Platform dependencies required by OpenLP (Qt/PySide, database/media/runtime
  dependencies per OS)

⚙️ Install and run
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install -e .
   python run_openlp.py

Alternative entrypoint:

.. code-block:: bash

   openlp

📥 EGW content import
---------------------

Import format documentation is included at:

* ``openlp/plugins/egwlibrary/resources/import_format.md``

A sample book file is included at:

* ``openlp/plugins/egwlibrary/resources/sample_book.json``

📄 Optional: Convert EGW PDF to JSON
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The repository includes a helper script:

.. code-block:: bash

   python scripts/egw_pdf_to_json.py en_DA.pdf --abbreviation DA --alias "Desire of Ages"

This script requires **PyMuPDF**:

.. code-block:: bash

   pip install PyMuPDF

📦 Building release artifacts
-----------------------------

Python package artifacts:

.. code-block:: bash

   hatch build -t sdist -t wheel

Windows Noir installer pipeline:

.. code-block:: powershell

   .\packaging\build.ps1

Outputs include:

* ``dist/openlp-<version>.tar.gz``
* ``dist/openlp-<version>-py3-none-any.whl``
* ``dist/installer/OpenLP-Noir-<version>-setup.exe``

📜 License
----------

This project remains GPL-licensed, following OpenLP's licensing model. See
``LICENSE`` for details.

💙 Credits
----------

This work builds on the OpenLP project and community. Upstream project:
https://openlp.org/
