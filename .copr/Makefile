srpm:
	dnf install -y git python3-setuptools
	mkdir -p .copr-build
	git archive --format=tar.gz --prefix=henzai-0.1.1/ -o .copr-build/henzai-0.1.1.tar.gz HEAD
	rpmbuild -bs --define "_sourcedir $(CURDIR)/.copr-build" --define "_srcrpmdir $(outdir)" henzai.spec
