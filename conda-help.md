conda env create -f env.yml

conda env remove --name myenv

conda env update --name myenv --file env.yml --prune
