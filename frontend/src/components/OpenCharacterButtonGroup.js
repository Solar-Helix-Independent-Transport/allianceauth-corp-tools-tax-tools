import React from "react";
import { Button, ButtonGroup } from "react-bootstrap";
import { OpenInGameButton } from "./OpenInGameButton";
import { ZKillButton, EveWhoButton } from "allianceauth-components";
export const OpenCharacterButtonGroup = ({ character_id, character_name }) => {
  return (
    <ButtonGroup bsSize="small" style={{ display: "flex" }}>
      <OpenInGameButton {...{ character_id }} />
      <Button disabled={character_id ? true : false} style={{ flexGrow: 1 }}>
        {character_name}
      </Button>
      <ZKillButton {...{ character_name }} />
      <EveWhoButton {...{ character_id }} />
    </ButtonGroup>
  );
};
