gitGraph
    commit id: "main"
    branch core-agent
    branch log-agent
    branch security-agent
    branch metrics-agent
    branch meta-agent
    checkout core-agent
    commit id: "feat(core)"
    checkout log-agent
    commit id: "feat(log)"
    checkout security-agent
    commit id: "feat(security)"
    checkout metrics-agent
    commit id: "feat(metrics)"
    checkout meta-agent
    commit id: "feat(meta)"
    checkout main
    merge core-agent
    merge log-agent
    merge security-agent
    merge metrics-agent
    merge meta-agent
