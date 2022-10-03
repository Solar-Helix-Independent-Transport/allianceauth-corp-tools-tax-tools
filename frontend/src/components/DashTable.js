import React, { useState } from "react";
import { Panel, Checkbox } from "react-bootstrap";
import { useQuery } from "react-query";
import { loadDash } from "../apis/Dashboard";
import { BaseTable } from "allianceauth-components";
import ReactTimeAgo from "react-time-ago";
import { StagingSelect } from "./StagingFilters";
import { OpenCharacterButtonGroup } from "./OpenCharacterButtonGroup";
export const Dashboard = () => {
  const { isLoading, error, data, isFetching } = useQuery(
    ["dashboard"],
    () => loadDash(),
    {
      refetchOnWindowFocus: false,
      initialData: {
        characters: [],
      },
    },
  );
  const [orphans, setOrphans] = useState(false);
  const [stagings, setStagings] = useState([]);

  const columns = React.useMemo(
    () => [
      {
        header: "Character",
        accessorKey: "char.name",
        cell: (props) => (
          <OpenCharacterButtonGroup
            character_id={props.row.original.char.id}
            character_name={props.getValue()}
          />
        ),
      },
      {
        header: "Main",
        accessorKey: "main.name",
        cell: (props) => (
          <OpenCharacterButtonGroup
            character_id={props.row.original.main.id}
            character_name={props.getValue()}
          />
        ),
      },
      {
        header: "Corp",
        accessorKey: "main.corp",
      },
      {
        header: "Alliance",
        accessorKey: "main.alli",
      },
      {
        header: "Location",
        accessorKey: "location.name",
      },
      {
        header: "Ship",
        accessorKey: "ship.name",
      },
      {
        header: "Death Clone",
        accessorKey: "death_clone.name",
      },
      {
        header: "Last Online",
        accessorKey: "logoff_date",
        enableColumnFilter: false,
        Cell: (props) => (
          <div style={{ whiteSpace: "nowrap" }}>
            {props.value ? (
              <ReactTimeAgo date={Date.parse(props.value)} />
            ) : (
              <></>
            )}
          </div>
        ),
      },
      {
        header: "Join Date",
        accessorKey: "start_date",
        enableColumnFilter: false,
        Cell: (props) => (
          <div style={{ whiteSpace: "nowrap" }}>
            {props.value ? (
              <ReactTimeAgo date={Date.parse(props.value)} />
            ) : (
              <></>
            )}
          </div>
        ),
      },
    ],
    [],
  );

  let graphData = data.characters;

  if (stagings.length > 0) {
    graphData = graphData.filter((row) => {
      return !stagings.includes(row.location.name);
    });
  }

  if (orphans) {
    graphData = graphData.filter((row) => {
      return !data.alliances.includes(row.main.alli_id);
    });
  }
  return (
    <Panel.Body>
      <div class={"col-xs-12"} style={{ display: "flex" }}>
        <div style={{ flexGrow: 1 }}>
          <StagingSelect
            data={data.stagings}
            setFilter={setStagings}
            labelText="Staging Filter"
            {...{ isFetching }}
          />
        </div>
        <Checkbox
          onChange={(e) => {
            setOrphans(e.target.checked);
          }}
        >
          Orphans Only
        </Checkbox>
      </div>
      <BaseTable
        data={graphData}
        {...{ isLoading, error, columns, isFetching }}
      />
    </Panel.Body>
  );
};
