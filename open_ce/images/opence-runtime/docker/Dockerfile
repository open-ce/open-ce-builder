FROM registry.access.redhat.com/ubi7/ubi

ENV CONDA_HOME=${CONDA_HOME:-/opt/conda}
ENV PATH=$CONDA_HOME/bin:$PATH

ENV OPEN_CE_CONDA_BUILD=3.20.5

ARG OPENCE_USER=builder
ARG LOCAL_CONDA_CHANNEL
ARG CONDA_ENV_FILE
ARG TARGET_DIR

ENV OPENCE_GROUP=${OPENCE_USER}
ARG GROUP_ID=1500
ARG USER_ID=1084

# GPUs
# nvidia-container-runtime
ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility
ENV NVIDIA_REQUIRE_CUDA "cuda>=10.2"

# Install basic requirements.
RUN export ARCH="$(uname -m)" && \
    yum repolist && yum install -y rsync openssh-clients sudo && \
    groupadd --non-unique --gid ${GROUP_ID} ${OPENCE_GROUP} && \
    # Adduser
    adduser -b /home/ --non-unique --create-home --gid ${GROUP_ID} --groups wheel \
    --uid ${USER_ID} ${OPENCE_USER} && \
    curl -o /tmp/anaconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${ARCH}.sh && \
    chmod +x /tmp/anaconda.sh && \
    /bin/bash /tmp/anaconda.sh -f -b -p /opt/conda && \
    rm -f /tmp/anaconda.sh && \
    $CONDA_HOME/bin/conda install -y conda-build=${OPEN_CE_CONDA_BUILD} && \
    chown -R ${OPENCE_USER}:${OPENCE_GROUP} ${CONDA_HOME}

USER ${OPENCE_USER}
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
    echo "export PYTHONPATH=${PYTHONPATH}:$HOME/open_ce" >> ${HOME}/.bashrc && \
    chown -R ${OPENCE_USER}:${OPENCE_GROUP} ${CONDA_HOME} && \
    echo ". $CONDA_HOME/etc/profile.d/conda.sh" >> ${HOME}/.bashrc && \
    echo "conda activate base" >> ${HOME}/.bashrc 
    
