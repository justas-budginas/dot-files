-- Crimson: suppress stock compositor artwork before the greeter maps.
hl.config({
    misc = {
        disable_hyprland_logo = true,
        disable_splash_rendering = true,
        background_color = "rgba(111318ff)",
    },
})

hl.on("hyprland.start", function()
    hl.exec_cmd("nwg-hello; hyprctl dispatch 'hl.dsp.exit()'")
end)
