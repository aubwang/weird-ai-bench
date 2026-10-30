from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

import pytest

from weird_ai_bench.cli import main
from weird_ai_bench.judge import _context
from weird_ai_bench.leaderboard import gate_stats, group_key
from weird_ai_bench.llm import ScriptedClient
from weird_ai_bench.orchestrate import ConfigError, RunConfig, Song, rescore
from weird_ai_bench.spec import (LineSpec, ProsodySetting, RhythmSpec, describe_rhythm,
                                 describe_line, load_spec, spec_from_dict)
from weird_ai_bench.verify import analyze_line, verify_section

EXAMPLE=Path(__file__).resolve().parents[1]/'examples/rhythm.yaml'


def run(mode='none', guidance='full', track='freeform'):
    client=ScriptedClient(['<lyrics>The stars shine clear\nWe head down town</lyrics>'])
    result=Song(RunConfig(['test/one'],scenario='none',track=track,rhythm=mode,guidance=guidance),
                client,spec=load_spec(EXAMPLE)).run()
    return result,client


@pytest.mark.parametrize('mode',['none','beats','grid','aligned'])
def test_prompt_formats_change_information_not_scores(mode):
    result,client=run(mode)
    baseline,_=run()
    assert result['scores']==baseline['scores']
    assert result['verification']==baseline['verification']
    assert result['scores']['strict_pass']
    prompts='\n'.join(m['content'] for c in client.calls for m in c['messages'])
    if mode=='none':
        assert 'rhythm in quarter-note beats' not in prompts and 'rhythm grid' not in prompts
    elif mode=='grid':
        assert 's L> s M' in prompts and '|0.5b|' in prompts
        assert 'q=0.25 beat' in prompts
    else:
        assert 'syllable onsets [0, 0.5, 2, 2.5]' in prompts
        assert '[[0.5], [1.5], [0.5], [1]]' in prompts
        assert ('source syllables by position 1:The' in prompts)==(mode=='aligned')
    # Fixed exact timing context for judges across all writer-format arms.
    assert _context(result)==_context(baseline)
    assert 'syllable onsets' in _context(result)
    assert result['spec_snapshot']['sections']['verse']['lines'][0]['prosody'][0]['rhythm']
    assert rescore(result)['verification']==result['verification']


def test_legacy_snapshots_defaults_and_no_rhythm_leak():
    spec=load_spec('two_voices')
    raw=asdict(spec)
    for sec in raw['sections'].values():
        for line in sec['lines']:line.pop('split_mode')
    assert spec_from_dict(raw)==spec
    result,client=run(guidance='none')
    prompts='\n'.join(m['content'] for c in client.calls for m in c['messages'])
    assert 'syllable onsets' not in prompts and 'Rhythm grid' not in prompts
    assert 'word boundary' not in prompts
    with pytest.raises(ConfigError,match='guidance full'):run('beats',guidance='none')
    with pytest.raises(ConfigError,match='timing data'):
        Song(RunConfig(['a','b'],rhythm='beats'),ScriptedClient([]),spec=spec)


def test_missing_reference_labels_and_invalid_mode_rejected_before_calls():
    spec=load_spec(EXAMPLE)
    spec.sections['verse'].lines[0].prosody[0].rhythm.reference_syllables=[]
    with pytest.raises(ConfigError,match='reference syllables'):
        Song(RunConfig(['a'],rhythm='aligned'),ScriptedClient([]),spec=spec)
    with pytest.raises(ConfigError,match='rhythm must be'):
        Song(RunConfig(['a'],rhythm='guess'),ScriptedClient([]),spec=spec)


def test_grouping_and_stats_separate_formats_and_preserve_old_default():
    runs=[run(m)[0] for m in ['none','beats','grid','aligned']]
    assert len({group_key(r) for r in runs})==4
    old=deepcopy(runs[0]);old['config'].pop('rhythm')
    assert group_key(old)==group_key(runs[0])
    assert {r['rhythm'] for r in gate_stats(runs)}=={'none','beats','grid','aligned'}
    different=deepcopy(runs[1])
    different['spec_snapshot']['sections']['verse']['lines'][0]['prosody'][0]['rhythm']['start_beat']=1
    assert group_key(different)!=group_key(runs[1])


def test_word_pause_allows_no_punctuation_but_not_a_split_word():
    word=LineSpec(4,split=[1,3],split_mode='word')
    punct=LineSpec(4,split=[1,3])
    assert analyze_line('Bright yellow sun',word).split_ok
    assert not analyze_line('Bright yellow sun',punct).split_ok
    assert not analyze_line('Yellow bright sun',word).split_ok
    assert not analyze_line('Yel-low bright sun',word).split_ok
    assert 'punctuation optional' in describe_line(word,1,{})
    assert 'comma or dash' in describe_line(punct,1,{})


def test_word_pause_retry_feedback_matches_rule():
    spec=load_spec(EXAMPLE)
    line=spec.sections['verse'].lines[1]
    line.prosody[0].split=[1,3]
    report=verify_section(['Yellow bright sun'],type(spec.sections['verse'])(
        'v','Verse',[line],{},singer=1))
    assert 'word boundary (punctuation optional)' in ' '.join(report.errors())


def test_pause_and_stress_require_same_pronunciation(monkeypatch):
    from weird_ai_bench.phonetics import Pron,Token,WordInfo
    first=Token(WordInfo('example','example',[Pron(('X',),(1,)),Pron(('X',),(0,0))],False,False),False)
    last=Token(WordInfo('example','example',[Pron(('X',),(1,1,1)),Pron(('X',),(1,1))],False,False),False)
    monkeypatch.setattr('weird_ai_bench.verify.tokenize',lambda *_:[first,last])
    line=LineSpec(4,stress=[1],split=[2,2],split_mode='word')
    report=analyze_line('example example',line)
    assert report.meter_passed(['syllables','stress'])
    assert report.meter_passed(['syllables','split'])
    assert not report.meter_passed(['syllables','stress','split'])


def test_rest_boundary_diagnostic_does_not_become_a_gate():
    setting=ProsodySetting('rest',[1]*4,rhythm=RhythmSpec([0,1,1.5,2],[[.5]]*4))
    line=LineSpec(prosody=[setting])
    good=analyze_line('Bright yellow sun',line)
    bad=analyze_line('Yellow bright sun',line)
    assert good.rest_boundary_positions==[1] and good.rest_boundary_ok
    assert bad.rest_boundary_ok is False and bad.meter_passed(['syllables','stress','split'])
    assert good.syllables_ok==bad.syllables_ok


@pytest.mark.parametrize('mutation',[
    {'onsets':[0,-1]}, {'onsets':[0,float('nan')]}, {'onsets':[True,.5]},
    {'onsets':[.5,1]}, {'durations':[[0],[1]]}, {'durations':[[float('inf')],[1]]},
    {'durations':[[True],[1]]}, {'durations':[[1]]}, {'durations':[[1],[1]]},
    {'start_beat':-1}, {'start_beat':4}, {'beats_per_bar':0},
    {'tempo_bpm':0}, {'tempo_bpm':-1}, {'tempo_bpm':float('nan')}, {'tempo_bpm':True},
    {'reference_syllables':['two words','x']}, {'reference_syllables':['x']},
])
def test_bad_timing_rejected(mutation):
    with pytest.raises(ValueError):RhythmSpec(**({'onsets':[0,.5],'durations':[[.5],[1]]}|mutation))


def test_timing_shape_unknown_fields_and_split_mode_validation():
    with pytest.raises(ValueError,match='notes per syllable'):
        ProsodySetting('wrong',[2,1],rhythm=RhythmSpec([0,.5],[[.5],[1]]))
    with pytest.raises(ValueError,match='split_mode'):
        LineSpec(4,split_mode='word')
    with pytest.raises(ValueError,match='split_mode'):
        ProsodySetting('bad',[1],split_mode='guess')
    raw=asdict(load_spec(EXAMPLE));raw['sections']['verse']['lines'][0]['prosody'][0]['rhythm']['typo']=1
    with pytest.raises(ValueError,match='rhythm needs'):spec_from_dict(raw)


def test_grid_is_lossless_for_note_lengths_and_melismas():
    rhythm=RhythmSpec([0,.75],[[.25,.5],[2.5]],start_beat=2.5)
    assert 'q+s>' in describe_rhythm(rhythm,'grid')
    assert '2.5b>' in describe_rhythm(rhythm,'grid')
    assert rhythm.rests()=={}


@pytest.mark.parametrize('text,count',[('fire hour',3),('our fire',3),('every hour',4),('the fire burns',4)])
def test_diagnostic_preserves_meter_selection_with_ambiguous_pronunciations(text,count):
    baseline=LineSpec(prosody=[ProsodySetting('reading',[1]*count,stress=[2])])
    timed=deepcopy(baseline)
    timed.prosody[0].rhythm=RhythmSpec([0]+[1+.5*i for i in range(count-1)],[[.5]]*count)
    before=asdict(analyze_line(text,baseline));after=asdict(analyze_line(text,timed))
    for report in [before,after]:
        report.pop('rest_boundary_positions');report.pop('rest_boundary_ok')
    assert after==before


def test_cli_preview_and_strict_freeform_prompt_parity(capsys):
    assert main(['run','--model','a','--spec',str(EXAMPLE),'--scenario','none','--rhythm','beats','--dry-run'])==0
    assert 'syllable onsets' in capsys.readouterr().out
    assert main(['spec','--spec',str(EXAMPLE),'--rhythm','grid'])==0
    assert 'rhythm grid' in capsys.readouterr().out
    _,free=run('beats');_,strict=run('beats',track='strict')
    assert free.calls[0]['messages']==strict.calls[0]['messages']
