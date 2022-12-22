from psychopy.experiment.exports import IndentingBuffer
from . import _TestBaseComponentsMixin, _TestDisabledMixin
from psychopy import experiment
import inspect


class _Generic(_TestBaseComponentsMixin, _TestDisabledMixin):
    def __init__(self, compClass):
        self.exp = experiment.Experiment()
        self.rt = experiment.routines.Routine(exp=self.exp, name="testRoutine")
        self.exp.addRoutine("testRoutine", self.rt)
        self.exp.flow.addRoutine(self.rt, 0)
        self.comp = compClass(exp=self.exp, parentName="testRoutine", name=f"test{compClass.__name__}")
        self.rt.addComponent(self.comp)


def test_all_components():
    for compName, compClass in experiment.getAllComponents().items():
        if compName == "SettingsComponent":
            continue
        # Make a generic testing object for this component
        tester = _Generic(compClass)
        # Run each method from _TestBaseComponentsMixin on tester
        for attr, meth in _TestBaseComponentsMixin.__dict__.items():
            if inspect.ismethod(meth):
                meth(tester)
        # Run each method from _TestBaseComponentsMixin on tester
        for attr, meth in _TestDisabledMixin.__dict__.items():
            if inspect.ismethod(meth):
                meth(tester)

def test_all_have_depth():
    # Define components which shouldn't have depth
    exceptions = ("PanoramaComponent",)
    # Create experiment
    exp = experiment.Experiment()
    rt = experiment.routines.Routine(exp=exp, name="testRoutine")
    exp.addRoutine("testRoutine", rt)
    exp.flow.addRoutine(rt, 0)
    # Add one of each component to the routine
    for compName, compClass in experiment.getAllComponents().items():
        # Settings components don't count so don't include one at all
        if compName in ("SettingsComponent",):
            continue
        comp = compClass(exp=exp, parentName="testRoutine", name=f"test{compClass.__name__}")
        rt.addComponent(comp)
    # For each component...
    for comp in rt:
        compName = type(comp).__name__
        # This won't be relevant for non-visual stimuli
        if compName in exceptions or not isinstance(comp, experiment.components.BaseVisualComponent):
            continue
        for target in ("PsychoPy", "PsychoJS"):
            # Skip if target isn't applicable
            if target not in comp.targets:
                continue
            # Crate buffer to get component code
            buff = IndentingBuffer(target=target)
            # Write init code
            if target == "PsychoJS":
                comp.writeInitCodeJS(buff)
                sought = "depth:"
            else:
                comp.writeInitCode(buff)
                sought = "depth="
            script = buff.getvalue()
            # Unless excepted, check that depth is in the output
            assert sought in script.replace(" ", ""), (
                f"Could not find any reference to depth in {target} init code for {compName}:\n"
                f"{script}\n"
                f"Any component drawn to the screen should be given a `depth` on init. If this component is a special "
                f"case, you can mark it as exempt by adding it to the `exceptions` variable in this test.\n"
            )


def test_indentation_consistency():
    """
    No component should exit any of its write methods at a different indent level as it entered, as this would break
    subsequent components / routines.
    """
    for compName, compClass in experiment.getAllComponents().items():
        if compName == "SettingsComponent":
            continue
        # Make a generic testing object for this component
        tester = _Generic(compClass)
        # Skip if component doesn't have a start/stop time
        if "startVal" not in tester.comp.params or "stopVal" not in tester.comp.params:
            continue
        # Check that each write method exits at the same indent level as it entered
        buff = IndentingBuffer(target="PsychoPy")
        msg = "Writing {} code for {} changes indent level by {} when start is `{}` and stop is `{}`."
        # Setup flow for writing
        tester.exp.flow.writeStartCode(buff)
        # Try combinations of start/stop being set/unset
        cases = [
            {"startVal": "0", "stopVal": "1"},
            {"startVal": "", "stopVal": "1"},
            {"startVal": "0", "stopVal": ""},
            {"startVal": "", "stopVal": ""},
        ]
        for case in cases:
            tester.comp.params["startType"].val = "time (s)"
            tester.comp.params["stopType"].val = "time (s)"
            for param, val in case.items():
                tester.comp.params[param].val = val
            # Init
            tester.comp.writeInitCode(buff)
            assert buff.indentLevel == 0, msg.format(
                "init", type(tester.comp).__name__, buff.indentLevel, case['startVal'], case['stopVal']
            )
            # Start routine
            tester.comp.writeRoutineStartCode(buff)
            assert buff.indentLevel == 0, msg.format(
                "routine start", type(tester.comp).__name__, buff.indentLevel, case['startVal'], case['stopVal']
            )
            # Each frame
            tester.comp.writeFrameCode(buff)
            assert buff.indentLevel == 0, msg.format(
                "each frame", type(tester.comp).__name__, buff.indentLevel, case['startVal'], case['stopVal']
            )
            # End routine
            tester.comp.writeRoutineEndCode(buff)
            assert buff.indentLevel == 0, msg.format(
                "routine end", type(tester.comp).__name__, buff.indentLevel, case['startVal'], case['stopVal']
            )
            # End experiment
            tester.comp.writeExperimentEndCode(buff)
            assert buff.indentLevel == 0, msg.format(
                "experiment end", type(tester.comp).__name__, buff.indentLevel, case['startVal'], case['stopVal']
            )
