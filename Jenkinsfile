pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    skipDefaultCheckout(true)
  }

  environment {
    APP_NAME = "rag_project-rag-app"
    HELM_RELEASE = "rag-app"
    HELM_NAMESPACE = "rag-helm"
    HELM_CHART = "helm/rag-app"
    HELM_VALUES = "helm/rag-app/values-prod.yaml"
    ROLLOUT_TIMEOUT = "180s"
    SMOKE_PATH = "/_stcore/health"
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
        script {
          env.GIT_SHA_SHORT = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
          env.IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_SHA_SHORT}"
          env.LOCAL_IMAGE = "${env.APP_NAME}:${env.IMAGE_TAG}"
          env.DEPLOY_IMAGE_REPO = env.DOCKER_REGISTRY?.trim() ? "${env.DOCKER_REGISTRY}/${env.APP_NAME}" : env.APP_NAME
          env.DEPLOY_IMAGE_TAG = env.IMAGE_TAG
          env.DEPLOY_IMAGE = "${env.DEPLOY_IMAGE_REPO}:${env.DEPLOY_IMAGE_TAG}"
          sh '''
            set -e
            printf '%s\n' "${LOCAL_IMAGE}" > .jenkins_local_image
            printf '%s\n' "${DEPLOY_IMAGE}" > .jenkins_deploy_image
            printf '%s\n' "${GIT_SHA_SHORT}" > .jenkins_commit
          '''
        }
      }
    }

    stage('Build') {
      steps {
        sh '''
          set -euo pipefail
          docker build -t "${LOCAL_IMAGE}" .
          docker image inspect "${LOCAL_IMAGE}" >/dev/null
        '''
      }
    }

    stage('Test') {
      steps {
        sh 'make check'
      }
    }

    stage('Scan') {
      steps {
        sh '''
          set -euo pipefail
          python -m pip install --upgrade pip
          python -m pip install pip-audit bandit
          pip-audit -r requirements.txt
          bandit -q -r core services app.py
        '''
      }
    }

    stage('Push') {
      when {
        expression { return (env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main' || env.CHANGE_TARGET == 'main') && env.DOCKER_REGISTRY?.trim() }
      }
      steps {
        sh '''
          set -euo pipefail
          if [ -z "${DOCKER_USERNAME:-}" ] || [ -z "${DOCKER_PASSWORD:-}" ]; then
            echo "Skip push: registry credentials not configured."
            exit 0
          fi
          echo "${DOCKER_PASSWORD}" | docker login "${DOCKER_REGISTRY}" -u "${DOCKER_USERNAME}" --password-stdin
          docker tag "${LOCAL_IMAGE}" "${DEPLOY_IMAGE}"
          docker push "${DEPLOY_IMAGE}"
        '''
      }
    }

    stage('Deploy') {
      when {
        expression { return env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main' || env.CHANGE_TARGET == 'main' }
      }
      steps {
        sh '''
          set -euo pipefail

          previous_revision="$(helm history "${HELM_RELEASE}" -n "${HELM_NAMESPACE}" 2>/dev/null | awk '$2=="deployed"{rev=$1} END{print rev}')"
          printf '%s\n' "${previous_revision:-}" > .jenkins_previous_revision

          if [ -n "${MINIKUBE_PROFILE:-}" ]; then
            minikube -p "${MINIKUBE_PROFILE}" image load "${LOCAL_IMAGE}"
          fi

          helm upgrade --install "${HELM_RELEASE}" "${HELM_CHART}" \
            -n "${HELM_NAMESPACE}" --create-namespace \
            -f "${HELM_VALUES}" \
            --set image.repository="${DEPLOY_IMAGE_REPO}" \
            --set image.tag="${DEPLOY_IMAGE_TAG}"

          helm history "${HELM_RELEASE}" -n "${HELM_NAMESPACE}" | tee .jenkins_helm_history_after_deploy
        '''
      }
    }

    stage('Smoke Test') {
      when {
        expression { return env.BRANCH_NAME == 'main' || env.GIT_BRANCH == 'origin/main' || env.CHANGE_TARGET == 'main' }
      }
      steps {
        sh '''
          set -euo pipefail
          kubectl -n "${HELM_NAMESPACE}" rollout status deployment/"${HELM_RELEASE}" --timeout="${ROLLOUT_TIMEOUT}"

          smoke_output="$(kubectl -n "${HELM_NAMESPACE}" run "smoke-${BUILD_NUMBER}" \
            --image=curlimages/curl:8.9.1 --restart=Never --rm -i \
            -- curl -fsS "http://${HELM_RELEASE}${SMOKE_PATH}" 2>&1)"
          printf '%s\n' "${smoke_output}" | tee .jenkins_smoke.log
        '''
      }
    }
  }

  post {
    failure {
      sh '''
        set +e
        previous_revision="$(cat .jenkins_previous_revision 2>/dev/null || true)"
        if [ -n "${previous_revision}" ]; then
          echo "Rollback target revision: ${previous_revision}"
          helm rollback "${HELM_RELEASE}" "${previous_revision}" -n "${HELM_NAMESPACE}" --wait --timeout="${ROLLOUT_TIMEOUT}"
          helm history "${HELM_RELEASE}" -n "${HELM_NAMESPACE}" | tee .jenkins_rollback_history
          kubectl -n "${HELM_NAMESPACE}" rollout status deployment/"${HELM_RELEASE}" --timeout="${ROLLOUT_TIMEOUT}"
        else
          echo "Skip rollback: no previous deployed revision recorded."
        fi
      '''
    }
    always {
      archiveArtifacts artifacts: '.jenkins_*', allowEmptyArchive: true
    }
  }
}