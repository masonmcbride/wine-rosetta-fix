// SPDX-License-Identifier: MIT
// Independent entry-window decode in a disposable, read-only imported program.
// @category WineResearch
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HexFormat;

public class AuditDxmtEntry extends GhidraScript {
  @Override public void run() throws Exception {
    String[] args = getScriptArgs();
    if (args.length != 4) throw new IllegalArgumentException("sha256 address byte-window output-json");
    String hash = currentProgram.getExecutableSHA256();
    if (!args[0].equalsIgnoreCase(hash)) throw new IllegalArgumentException("Input hash mismatch");
    if (currentProgram.getDefaultPointerSize() != 4) throw new IllegalArgumentException("Expected PE32");
    Address start = toAddr(args[1]);
    int length = Integer.parseInt(args[2]);
    if (length < 1 || length > 1024) throw new IllegalArgumentException("Invalid window");
    if (!disassemble(start)) throw new IllegalStateException("Disassembly failed");
    JsonObject result = new JsonObject();
    result.addProperty("sha256", hash);
    result.addProperty("language", currentProgram.getLanguageID().toString());
    result.addProperty("image_base", currentProgram.getImageBase().toString());
    result.addProperty("start", start.toString());
    result.addProperty("byte_window", length);
    result.addProperty("scope", "Independent entry-window decode; not function-cost or gameplay attribution");
    JsonArray instructions = new JsonArray();
    InstructionIterator iterator = currentProgram.getListing().getInstructions(
        new AddressSet(start, start.add(length - 1)), true);
    while (iterator.hasNext()) {
      Instruction instruction = iterator.next();
      JsonObject row = new JsonObject();
      row.addProperty("address", instruction.getAddress().toString());
      row.addProperty("bytes", HexFormat.of().formatHex(instruction.getBytes()));
      row.addProperty("text", instruction.toString());
      JsonArray calls = new JsonArray();
      for (Reference reference : instruction.getReferencesFrom()) {
        if (reference.getReferenceType().isCall()) calls.add(reference.getToAddress().toString());
      }
      row.add("call_targets", calls);
      instructions.add(row);
    }
    if (instructions.size() == 0) throw new IllegalStateException("Empty disassembly");
    result.add("instructions", instructions);
    Files.writeString(Path.of(args[3]), new GsonBuilder().setPrettyPrinting().create().toJson(result) + "\n");
    println("DXMT entry audit saved: " + args[3]);
  }
}
