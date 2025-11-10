# modify /home/moss/mini-swe-agent/src/minisweagent/config/extra/swebench.yaml
mini-extra swebench-single \
    --subset verified \
    --split test \
    --model  openrouter/openai/gpt-5-mini\
    -i sympy__sympy-15599