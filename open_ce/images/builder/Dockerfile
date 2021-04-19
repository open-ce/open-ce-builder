FROM registry.access.redhat.com/ubi7/ubi

ENV CONDA_HOME=${CONDA_HOME:-/opt/conda}
ENV PATH=$CONDA_HOME/bin:$PATH

ENV OPEN_CE_CONDA_BUILD=3.20.5

RUN export ARCH="$(uname -m)" && \
    curl -o /tmp/anaconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${ARCH}.sh && \
    chmod +x /tmp/anaconda.sh && \
    /bin/bash /tmp/anaconda.sh -f -b -p /opt/conda && \
    rm -f /tmp/anaconda.sh && \
    $CONDA_HOME/bin/conda install -y conda-build=${OPEN_CE_CONDA_BUILD} networkx git patch

RUN export PATH="${PATH}" && \
    echo "PATH="${PATH}"" >> ${HOME}/.profile && \
    $CONDA_HOME/bin/conda config --system --add envs_dirs $CONDA_HOME/envs && \
    $CONDA_HOME/bin/conda config --system --add pkgs_dirs $CONDA_HOME/pkgs && \
    $CONDA_HOME/bin/conda config --system --set always_yes true && \
    $CONDA_HOME/bin/conda config --system --set auto_update_conda false && \
    $CONDA_HOME/bin/conda config --system --set notify_outdated_conda false && \
    $CONDA_HOME/bin/conda --version && \
    mkdir -p $CONDA_HOME/conda-bld && \
    mkdir -p $HOME/.cache && \
    echo "export PYTHONPATH=${PYTHONPATH}:$HOME/open_ce" >> ${HOME}/.bashrc
