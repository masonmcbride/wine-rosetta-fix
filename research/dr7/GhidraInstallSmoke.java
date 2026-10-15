import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;

public class GhidraInstallSmoke extends GhidraScript {
    public void run() throws Exception {
        DecompInterface decompiler = new DecompInterface();
        try {
            if (!decompiler.openProgram(currentProgram)) throw new Exception(decompiler.getLastMessage());
            for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
                if (function.getName().equals("_baseline") || function.getName().equals("baseline")) {
                    DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
                    if (!result.decompileCompleted()) throw new Exception(result.getErrorMessage());
                    println("NATIVE_DECOMPILER_SMOKE_PASS " + function.getEntryPoint());
                    return;
                }
            }
            throw new Exception("Baseline function missing");
        } finally {
            decompiler.dispose();
        }
    }
}
