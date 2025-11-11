pip install -e . 'full'
mini-extra swebench-single \
    --subset verified \
    --split test \
    --model  gpt-4o-mini\
    -i sympy__sympy-15599