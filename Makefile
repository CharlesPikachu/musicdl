.PHONY: install

install:
	python setup.py install

develop:
	python setup.py develop

publish:
	pip install 'twine>=1.5.0' --upgrade
	python setup.py sdist bdist_wheel
	twine upload dist/*